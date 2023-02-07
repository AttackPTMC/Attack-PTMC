# coding=utf-8
# @Time    : 2020/7/8
# @Author  : Zhou Yang
# @Email   : zyang@smu.edu.sg
# @File    : attack.py
'''For attacking CodeBERT models'''
import os
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
import json
import sys
sys.path.append('../../../')
sys.path.append('../code')
sys.path.append('../../../python_parser')
retval = os.getcwd()

import csv
import logging
import argparse
import warnings
import pickle
import copy
import torch
import multiprocessing
import time
import numpy as np
from run_parser import get_identifiers, get_example
from model import Model
from utils import set_seed, build_vocab
from utils import Recorder, CodeDataset
from run import TextDataset
from attacker import WIR_Attacker, get_code_pairs, convert_examples_to_features
from transformers import RobertaForMaskedLM
from transformers import (RobertaConfig, RobertaModel, RobertaTokenizer)

warnings.simplefilter(action='ignore', category=FutureWarning)  # Only report warning

MODEL_CLASSES = {
    'roberta': (RobertaConfig, RobertaModel, RobertaTokenizer)
}

logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser()

    ## Required parameters
    parser.add_argument("--output_dir", default=None, type=str, required=True,
                        help="The output directory where the model predictions and checkpoints will be written.")

    ## Other parameters
    parser.add_argument("--eval_data_file", default=None, type=str,
                        help="An optional input evaluation data file to evaluate the perplexity on (a text file).")
    parser.add_argument("--test_data_file", default=None, type=str,
                        help="An optional input evaluation data file to evaluate the perplexity on (a text file).")
    parser.add_argument("--base_model", default=None, type=str,
                        help="Base Model")
    parser.add_argument("--model_type", default="bert", type=str,
                        help="The model architecture to be fine-tuned.")
    parser.add_argument("--model_name_or_path", default=None, type=str,
                        help="The model checkpoint for weights initialization.")
    parser.add_argument("--csv_store_path", default=None, type=str,
                        help="Base Model")
    parser.add_argument("--use_ga", action='store_true',
                        help="Whether to GA-Attack.")
    parser.add_argument("--mlm", action='store_true',
                        help="Train with masked-language modeling loss instead of language modeling.")
    parser.add_argument("--mlm_probability", type=float, default=0.15,
                        help="Ratio of tokens to mask for masked language modeling loss")

    parser.add_argument("--config_name", default="", type=str,
                        help="Optional pretrained config name or path if not the same as model_name_or_path")
    parser.add_argument("--tokenizer_name", default="", type=str,
                        help="Optional pretrained tokenizer name or path if not the same as model_name_or_path")
    parser.add_argument("--cache_dir", default="", type=str,
                        help="Optional directory to store the pre-trained models downloaded from s3 (instread of the default one)")
    parser.add_argument("--block_size", default=-1, type=int,
                        help="Optional input sequence length after tokenization."
                             "The training dataset will be truncated in block of this size for training."
                             "Default to the model max input length for single sentence inputs (take into account special tokens).")
    parser.add_argument("--do_train", action='store_true',
                        help="Whether to run training.")
    parser.add_argument("--do_eval", action='store_true',
                        help="Whether to run eval on the dev set.")
    parser.add_argument("--do_test", action='store_true',
                        help="Whether to run eval on the dev set.")
    parser.add_argument("--evaluate_during_training", action='store_true',
                        help="Run evaluation during training at each logging step.")
    parser.add_argument("--eval_batch_size", default=4, type=int,
                        help="Batch size per GPU/CPU for evaluation.")
    parser.add_argument('--seed', type=int, default=42,
                        help="random seed for initialization")

    args = parser.parse_args()

    device = torch.device("cuda")
    args.device = device

    # Set seed
    set_seed(args.seed)

    config_class, model_class, tokenizer_class = MODEL_CLASSES[args.model_type]
    config = config_class.from_pretrained(args.config_name if args.config_name else args.model_name_or_path,
                                          cache_dir=args.cache_dir if args.cache_dir else None)
    config.num_labels = 2
    tokenizer = tokenizer_class.from_pretrained(args.tokenizer_name,
                                                do_lower_case=False,
                                                cache_dir=args.cache_dir if args.cache_dir else None)
    if args.block_size <= 0:
        args.block_size = tokenizer.max_len_single_sentence  # Our input block size will be the max possible for the model
    args.block_size = min(args.block_size, tokenizer.max_len_single_sentence)
    if args.model_name_or_path:
        model = model_class.from_pretrained(args.model_name_or_path,
                                            from_tf=bool('.ckpt' in args.model_name_or_path),
                                            config=config,
                                            cache_dir=args.cache_dir if args.cache_dir else None)
    else:
        model = model_class(config)

    model = Model(model, config, tokenizer, args)

    checkpoint_prefix = 'checkpoint-best-f1/model.bin'
    output_dir = os.path.join(args.output_dir, '{}'.format(checkpoint_prefix))
    model.load_state_dict(torch.load(output_dir))
    model.to(args.device)
    logger.info("reload model from {}".format(output_dir))

    cpu_cont = 16

    # Load Dataset
    ## Load Dataset
    pool = multiprocessing.Pool(cpu_cont)
    eval_dataset = TextDataset(tokenizer, args, args.eval_data_file, pool = pool)
    ## Load code pairs
    source_codes = get_code_pairs(args.eval_data_file, tokenizer, args)
    assert len(source_codes) == len(eval_dataset)

    code_tokens = []
    for index, code in enumerate(source_codes):
        code_tokens.append(get_identifiers(code[2], "java")[1])

    id2token, token2id = build_vocab(code_tokens, 5000)

    success_attack = 0
    total_cnt = 0

    recoder = Recorder(args.csv_store_path)
    attacker = WIR_Attacker(args, model, tokenizer, token2id, id2token)
    start_time = time.time()
    query_times = 0
    for index, example in enumerate(eval_dataset):
        print("Index: ", index)
        example_start_time = time.time()
        code_pair = source_codes[index]
        logits, preds = model.get_results([example], args.eval_batch_size)
        orig_label = preds[0]
        true_label = example[1].item()
        if not orig_label == true_label:
            continue
        first_code = code_pair[2]

        code_2 = code_pair[3]
        code_2 = " ".join(code_2.split())
        words_2 = tokenizer.tokenize(code_2)

        identifiers, orig_code_tokens = get_identifiers(first_code, 'java')
        identifiers = [iden[0] for iden in identifiers]
        if len(identifiers) == 0:
            continue
        total_cnt += 1
        print("identifier:", identifiers)

        code, prog_length, adv_code, true_label, orig_label, temp_label, is_success, variable_names, names_to_importance_score, nb_changed_var, nb_changed_pos, replaced_words = attacker.wir_random_attack(
            example, code_pair)

        example_end_time = (time.time() - example_start_time) / 60
        print("Example time cost: ", round(example_end_time, 2), "min")
        print("ALL examples time cost: ", round((time.time() - start_time) / 60, 2), "min")
        print("Query times in this attack: ", model.query - query_times)

        replace_info = ''
        if replaced_words is not None:
            for key in replaced_words.keys():
                replace_info += key + ':' + replaced_words[key] + ','

        if is_success == 1:
            success_attack += 1
            recoder.write(index, first_code, adv_code, len(orig_code_tokens), len(identifiers),
                          replace_info, model.query - query_times, example_end_time, "WIR")

            # temp_replace = " ".join(adv_code.split())
            # temp_replace = tokenizer.tokenize(temp_replace)
            # new_feature = convert_examples_to_features(temp_replace, words_2, true_label, None, None, tokenizer,
            #                                            args, None)
            # new_example = CodeDataset([new_feature])
            # logits, preds = model.get_results([new_example[0]], args.eval_batch_size)
            # adv_label = preds[0]
            # print("attack predict label: ", adv_label)
            # if adv_label != true_label:
            #     print("true adv!")
            # else:
            #     print("false adv!")

        else:
            recoder.write(index, None, None, len(orig_code_tokens), len(identifiers),
                          None, model.query - query_times, example_end_time, "0")
        query_times = model.query
        print("Success rate: {}/{} = {}".format(success_attack, total_cnt, 1.0 * success_attack / total_cnt))
    print("Final success rate: {}/{} = {}".format(success_attack, total_cnt, 1.0 * success_attack / total_cnt))
if __name__ == '__main__':
    main()