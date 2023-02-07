import os

os.system("CUDA_VISIBLE_DEVICES=2 python attack_style.py \
    --output_dir=../saved_models \
    --model_type=roberta \
    --tokenizer_name=microsoft/codebert-base \
    --model_name_or_path=microsoft/codebert-base \
    --base_model=microsoft/codebert-base-mlm \
    --csv_store_path1 result/attack_style_all.csv \
    --eval_data_file=../../../dataset/Clone-detection/test_sampled.txt \
    --block_size 512 \
    --eval_batch_size 2 \
    --seed 123456  2>&1")

