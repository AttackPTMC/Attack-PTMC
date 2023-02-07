from utils import CodeDataset, is_valid_identifier
import random
import copy
from run import InputFeatures, convert_examples_to_features
import pandas as pd
import operator
from run_parser import get_example
from utils import get_code_tokens

def get_statement_identifier(first_idx, identifiers):
    file = "../../../dataset/Clone-detection/data.csv"
    df = pd.read_csv(file, encoding="utf-8")
    idx_list = df["idx"].tolist()
    method_statements = df["Method_statement"].tolist()
    return_statements = df["Return_statement"].tolist()
    if_statements = df["If_statement"].tolist()
    throw_statements = df["Throw_statement"].tolist()
    try_statements = df["Try_statement"].tolist()
    for_statements = df["For_statement"].tolist()
    statement_dict = {}
    for i, idx in enumerate(idx_list):
        if idx == first_idx:
            for_statement = for_statements[i][1:-1].replace(" ", "").split(",")
            for_statement = [var for var in for_statement if var in identifiers]
            if len(for_statement) > 0:
                statement_dict["For"] = for_statement
            try_statement = try_statements[i][1:-1].replace(" ", "").split(",")
            try_statement = [var for var in try_statement if var in identifiers]
            if len(try_statement) > 0:
                statement_dict["Try"] = try_statement
            if_statement = if_statements[i][1:-1].replace(" ", "").split(",")
            if_statement = [var for var in if_statement if var in identifiers]
            if len(if_statement) > 0:
                statement_dict["If"] = if_statement
            method_statement = method_statements[i][1:-1].replace(" ", "").split(",")
            method_statement = [var for var in method_statement if var in identifiers]
            if len(method_statement) > 0:
                statement_dict["Method"] = method_statement
            throw_statement = throw_statements[i][1:-1].replace(" ", "").split(",")
            throw_statement = [var for var in throw_statement if var in identifiers]
            if len(throw_statement) > 0:
                statement_dict["Throw"] = throw_statement
            return_statement = return_statements[i][1:-1].replace(" ", "").split(",")
            return_statement = [var for var in return_statement if var in identifiers]
            if len(return_statement) > 0:
                statement_dict["Return"] = return_statement
            value_list = [i for p in list(statement_dict.values()) for i in p]
            other_statement = [var for var in identifiers if var not in value_list]
            if len(other_statement) > 0:
                statement_dict["Other"] = other_statement
    return statement_dict

class Beam_Attacker(object):
    def __init__(self, args, model_tgt, tokenizer_tgt):
        self.args = args
        self.model_tgt = model_tgt
        self.tokenizer_tgt = tokenizer_tgt

    def is_vaild(self, code_token, identifier):
        if not is_valid_identifier(identifier):
            return False
        position = []
        for index, token in enumerate(code_token):
            if identifier == token:
                position.append(index)
        if all(x > self.args.block_size-2 for x in position):
            return False
        return True

    def perturb(self, example, code_1, words_2, all_substitues, tgt_word):
        is_success = -1
        final_code = copy.deepcopy(code_1)
        logits, preds = self.model_tgt.get_results([example], self.args.eval_batch_size)
        orig_prob = logits[0]
        orig_label = preds[0]
        current_prob = max(orig_prob)

        most_gap = 0.0
        candidate = None
        replace_examples = []
        substitute_list = []

        for substitute in all_substitues[:30]:
            if not is_valid_identifier(substitute.strip()):
                continue
            substitute_list.append(substitute.strip())
            temp_replace = get_example(final_code, tgt_word, substitute.strip())
            temp_replace = " ".join(temp_replace.split())
            temp_replace = self.tokenizer_tgt.tokenize(temp_replace)
            new_feature = convert_examples_to_features(temp_replace,
                                                       words_2,
                                                       example[1].item(),
                                                       None, None,
                                                       self.tokenizer_tgt,
                                                       self.args, None)
            replace_examples.append(new_feature)
        new_dataset = CodeDataset(replace_examples)
        logits, preds = self.model_tgt.get_results(new_dataset, self.args.eval_batch_size)
        for index, temp_prob in enumerate(logits):
            temp_label = preds[index]
            if temp_label != orig_label:
                is_success = 1
                candidate = substitute_list[index]
                adv_code = get_example(final_code, tgt_word, candidate)
                return is_success, adv_code, candidate, temp_prob[orig_label]
            else:
                gap = current_prob - temp_prob[temp_label]
                if gap > most_gap:
                    most_gap = gap
                    candidate = substitute_list[index]

        if most_gap > 0:

            current_prob = current_prob - most_gap
            final_code = get_example(final_code, tgt_word, candidate)
            return is_success, final_code, candidate, current_prob
        else:
            is_success = -2
            return is_success, None, None, None

    def greedy_attack(self, orig_prob, example, substitutes, code_pair, statement_dict):
        label = example[1].item()
        result = {"succ": -1}
        code_1 = code_pair[2]
        code_2 = code_pair[3]
        words_2 = self.tokenizer_tgt.tokenize(code_2)

        # start greedy attack
        greedy_replace_info = ""
        greedy_identifiers = list(statement_dict.values())
        greedy_identifiers = [i for j in greedy_identifiers for i in j]
        greedy_identifiers = [i for n, i in enumerate(greedy_identifiers) if i not in greedy_identifiers[:n]]
        tmp_example = example
        tmp_code = code_1
        code_token = get_code_tokens(tmp_code)
        for greedy_identifier in greedy_identifiers:
            if not self.is_vaild(code_token, greedy_identifier):
                continue
            is_success, final_code, candidate, current_prob = self.perturb(tmp_example, tmp_code, words_2,
                                                                           substitutes[greedy_identifier], greedy_identifier, 30)
            if candidate is not None:
                greedy_replace_info += greedy_identifier + ':' + candidate + ','
                if is_success == 1:
                    print("%s SUC! %s (%.5f => %.5f)" % \
                          ('>>', greedy_replace_info, orig_prob, current_prob), flush=True)
                    result["succ"] = 1
                    result["adv_code"] = final_code
                    result["replace_info"] = greedy_replace_info
                    result["type"] = "Greedy"
                    return result
                tmp_code = final_code
                temp_replace = " ".join(get_code_tokens(final_code))
                temp_replace = self.tokenizer_tgt.tokenize(temp_replace)
                new_feature = convert_examples_to_features(temp_replace, words_2, label, None, None, self.tokenizer_tgt, self.args, None)
                tmp_example = CodeDataset([new_feature])[0]
            else:
                temp_replace = " ".join(get_code_tokens(tmp_code))
                temp_replace = self.tokenizer_tgt.tokenize(temp_replace)
                new_feature = convert_examples_to_features(temp_replace, words_2, label, None, None, self.tokenizer_tgt, self.args, None)
                tmp_example = CodeDataset([new_feature])[0]
        return result

    def beam_attack(self, orig_prob, example, substitutes, code_pair, statement_dict, beam_size):
        label = example[1].item()
        result = {"succ": -1}
        code_1 = code_pair[2]
        code_2 = code_pair[3]
        code_2 = " ".join(code_2.split())
        words_2 = self.tokenizer_tgt.tokenize(code_2)

        # start beam attack
        iter = 0
        init_pop = {}
        final_pop = {}
        used_iden = []
        replace_info = ""
        tmp_code = code_1
        code_token = get_code_tokens(tmp_code)
        for key, identifiers in statement_dict.items():
            if iter == 0:
                used_iden += identifiers
                for identifier in identifiers:
                    if not self.is_vaild(code_token, identifier):
                        continue
                    is_success, final_code, candidate, current_prob = self.perturb(example, tmp_code, words_2,
                                                                                   substitutes[identifier], identifier)
                    if candidate is not None:
                        sequence = [iden for iden in identifiers if iden != identifier]
                        replace_info = identifier + ':' + candidate + ','
                        init_pop[replace_info] = {"adv_code": final_code, "prob": current_prob,
                                                  "original_var": [identifier],
                                                  "adv_var": [candidate], "sequence": sequence}
                        if is_success == 1:
                            print("%s SUC! %s => %s (%.5f => %.5f)" % \
                                  ('>>', identifier, candidate,
                                   orig_prob,
                                   current_prob), flush=True)
                            result["succ"] = 1
                            result["adv_code"] = final_code
                            result["replace_info"] = replace_info
                            result["type"] = "Beam"
                            return result
                    else:
                        init_pop["noChange"] = {"adv_code": code_1, "prob": orig_prob, "original_var": [],
                                                "adv_var": [], "sequence": identifiers}

                final_pop = dict(sorted(init_pop.items(), key=lambda x: x[1]['prob'])[:beam_size])

            num_iter = len(identifiers) - 1
            if iter > 0:
                tmp_pop = {}
                identifiers = [iden for iden in identifiers if iden not in used_iden]
                used_iden += identifiers
                final_pop_copy = copy.copy(final_pop)
                if len(final_pop_copy) == 0:
                    tmp_pop["noChange"] = {"adv_code": code_1, "prob": orig_prob, "original_var": [],
                                           "adv_var": [], "sequence": identifiers}
                for replace_info, value in final_pop_copy.items():
                    tmp_pop[replace_info] = {"adv_code": value["adv_code"], "prob": value["prob"],
                                             "original_var": value["original_var"],
                                             "adv_var": value["adv_var"], "sequence": identifiers}
                final_pop = tmp_pop
                num_iter = len(identifiers)
            # for replace_info, value in final_pop.items():
            #     print("----", iter, replace_info, value["original_var"], value["sequence"], value["prob"])
            # print("num_iter:", iter)
            for i_iter in range(num_iter):
                tmp_pop = {}
                final_pop_copy = copy.copy(final_pop)
                for replace_info, value in final_pop_copy.items():
                    if len(value["sequence"]) == 0:
                        continue
                    for seq in value["sequence"]:
                        if not self.is_vaild(code_token, seq):
                            continue
                        temp_replace = " ".join(value["adv_code"].split())
                        temp_replace = self.tokenizer_tgt.tokenize(temp_replace)
                        new_feature = convert_examples_to_features(temp_replace, words_2, label, None, None,
                                                                   self.tokenizer_tgt, self.args, None)
                        new_example = CodeDataset([new_feature])
                        is_success, final_code, candidate, current_prob = self.perturb(new_example[0], value["adv_code"],
                                                                                       words_2, substitutes[seq], seq)
                        if candidate is not None:
                            original_var = value["original_var"] + [seq]
                            adv_var = value["adv_var"] + [candidate]
                            new_replace_info = ''
                            for info_i in range(len(original_var)):
                                new_replace_info += original_var[info_i] + ':' + adv_var[info_i] + ','
                            sequence = [iden for iden in value["sequence"] if iden not in original_var]
                            tmp_pop[new_replace_info] = {"adv_code": final_code, "prob": current_prob,
                                                         "original_var": original_var,
                                                         "adv_var": adv_var, "sequence": sequence}
                            if is_success == 1:
                                print("%s SUC! %s => %s (%.5f => %.5f)" % \
                                      ('>>', original_var, adv_var,
                                       orig_prob,
                                       current_prob), flush=True)
                                result["succ"] = 1
                                result["adv_code"] = final_code
                                result["replace_info"] = new_replace_info
                                result["type"] = "Beam"
                                return result
                        else:
                            tmp_pop[replace_info] = value

                select_dict = dict(list(tmp_pop.items()) + list(final_pop_copy.items()))
                final_pop = dict(sorted(select_dict.items(), key=lambda x: x[1]['prob'])[:beam_size])
                if operator.eq(list(final_pop.keys()), list(final_pop_copy.keys())):
                    break
                if i_iter != num_iter:
                    duplicate_key = [i for i in list(final_pop.keys()) if i in list(final_pop_copy.keys())]
                    if len(duplicate_key) > 0:
                        for pop_key in duplicate_key:
                            del final_pop[pop_key]
                # for replace_info, value in final_pop.items():
                #     print("iter select:", i_iter, replace_info, value["original_var"], value["sequence"], value["prob"])

            final_pop = final_pop
            iter += 1

        return result
