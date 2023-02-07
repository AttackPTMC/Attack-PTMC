import os

os.system("python run.py \
    --output_dir=../saved_models/ \
    --model_type=gpt2 \
    --tokenizer_name=microsoft/CodeGPT-small-java-adaptedGPT2 \
    --model_name_or_path=microsoft/CodeGPT-small-java-adaptedGPT2 \
    --do_eval \
    --do_test \
    --train_data_file=../../../dataset/Defect-detection/train.jsonl \
    --eval_data_file=../../../dataset/Defect-detection/valid.jsonl \
    --test_data_file=../../../dataset/Defect-detection/test.jsonl \
    --epoch 5 \
    --block_size 400 \
    --train_batch_size 32 \
    --eval_batch_size 64 \
    --learning_rate 2e-5 \
    --max_grad_norm 1.0 \
    --evaluate_during_training \
    --seed 123456 2>&1")

