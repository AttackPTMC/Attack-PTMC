import os

os.system("python substitution_CodeGPT.py \
    --output_dir=CodeGPT/Clone_detection/saved_models/ \
    --model_type=gpt2 \
    --config_name=microsoft/CodeGPT-small-java-adaptedGPT2 \
    --model_name_or_path=microsoft/CodeGPT-small-java-adaptedGPT2 \
    --tokenizer_name=microsoft/CodeGPT-small-java-adaptedGPT2 \
    --do_train \
    --train_data_file=../../../dataset/Clone-detection/train.txt \
    --eval_data_file=../../../dataset/Clone-detection/valid.txt \
    --test_data_file=../../../dataset/Clone-detection/test.txt \
    --epoch 2 \
    --block_size 400 \
    --train_batch_size 16 \
    --eval_batch_size 2 \
    --learning_rate 5e-5 \
    --max_grad_norm 1.0 \
    --evaluate_during_training \
    --seed 123456 2>&1")

