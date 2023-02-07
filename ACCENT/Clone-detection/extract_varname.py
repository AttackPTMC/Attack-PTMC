import javalang as javalang
import pandas as pd
import os
from utils import get_sequence as func
import time

def trans_to_sequences(ast):
    sequence = []
    func(ast, sequence)
    return sequence

def extract_var_name(file,root,save_var_path,save_all_path):
    f_code = open(file, 'r')
    set_var = set()
    var_list = []
    index_list = []
    count = 0

    for line in f_code:

        code = line
        var = []
        #func name
        methodname_index = -1
        code_split = line.split(' ')
        for i in range(len(code_split)):
            if code_split[i] == '(':
                methodname_index = i - 1
                break
        if methodname_index == -1:
            print('can not find function name:' + str(count))
        else:
            var.append(code_split[methodname_index])
            set_var.add(code_split[methodname_index])
        print("code_split",code_split)
        print("methodname_index",methodname_index)
        print("code_split[methodname_index]",code_split[methodname_index])
        # print(var)
        tokens = javalang.tokenizer.tokenize(code)
        parser = javalang.parser.Parser(tokens)
        tree = parser.parse_member_declaration()
        ast_list = trans_to_sequences(tree)
        # print(tokens)
        # print(parser)
        # print(tree)
        # print(ast_list)

        for i in range(len(ast_list)):
            item = ast_list[i]
            if item == 'VariableDeclarator':
                var.append(ast_list[i + 1])
                set_var.add(ast_list[i + 1])

        # function name

        print(var)
        var_list.append(var)
        index_list.append(count)
        count = count + 1
        print('ok  ' + str(count))

    if not os.path.exists(root + '/var_name'):
        os.mkdir(root + '/var_name')

    data_var = pd.DataFrame({'id': index_list, 'variable': var_list})
    data_var.to_pickle(save_var_path)

    var_all_list = list(set_var)
    data_var_all = pd.DataFrame({'id': 0, 'all vars': [var_all_list]})
    data_var_all.to_pickle(save_all_path)

if __name__=='__main__':
    root = '../Clone-detection'
    totaltime = 0
    totaltime2 = 0
    start_num = 11
    end_num = 12
    for mycnt in range(start_num, end_num):
        start = time.process_time()
        start2 = time.time()
        print('start at time:')
        print(time.strftime(' %Y-%m-%d %H:%M:%S', time.localtime(time.time())))
        # file=root+'/data1/java' + str(mycnt) + '/test/code.original'
        file=root+'/data1/java' + str(mycnt) + '/test/code.original'
        # file=root+'/data1/java/test/code.original_test'
        save_all_path=root+'/var_for_allCode_test' + str(mycnt) + '.pkl'
        save_var_path=root+'/var_for_everyCode_test' + str(mycnt) + '.pkl'
        print('extract var name :')
        extract_var_name(file,root,save_var_path,save_all_path)
        print('extract end!')
        print('end...')
        print(time.strftime(' %Y-%m-%d %H:%M:%S', time.localtime(time.time())))
        end = time.process_time()
        end2 = time.time()
        totaltime += end - start
        totaltime2 += end2 - start2
        print("time cost: ", end - start)
        print("time cost2: ", end2 - start2)
    print("total time: ", totaltime)
    print("total time2: ", totaltime2)
    print("avg time: ", totaltime / (end_num - start_num))
    print("avg time: ", totaltime2 / (end_num - start_num))
