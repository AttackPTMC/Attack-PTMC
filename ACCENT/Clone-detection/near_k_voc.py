import pandas as pd
import numpy as np
from gensim.models.word2vec import Word2Vec
import random
import os
import time
from sklearn.metrics.pairwise import cosine_similarity

root = '../Clone-detection'
# k=5
k=30
def get_topk_index(k,arr):
    top_k=k
    array=arr
    top_k_index=array.argsort()[::-1][0:top_k]
    return top_k_index   #return top-k use list[]


totaltime = 0.0
totaltime2 = 0
start_num = 11
end_num = 12
for mycnt in range(start_num, end_num):
    start = time.process_time()
    start2 = time.time()
    print('read embedding....')
    print('start at time:')
    print(time.strftime(' %Y-%m-%d %H:%M:%S', time.localtime(time.time())))
    word2vec = Word2Vec.load(root+'/data1/java1/node_w2v_64').wv
    vocab=word2vec.key_to_index
    max_token=word2vec.vectors.shape[0]
    embedding_dim=word2vec.vectors.shape[1]
    embeddings = np.zeros((max_token+1,embedding_dim))
    embeddings[:max_token]=word2vec.vectors
    print('end read embedding..')

    print('read all var and extract embedding..')
    data_all_var=pd.read_pickle(root+'/var_for_allCode_test' + str(mycnt) + '.pkl')
    all_var_list=list(data_all_var['all vars'].tolist()[0])
    max_var=len(all_var_list)
    embeddings_allvar=np.zeros((max_var,embedding_dim))
    index_all_var=[]
    for item in all_var_list:
        if item in vocab:
            index_all_var.append(vocab[item])
        else:
            index_all_var.append(max_token)

    for i in range(max_var):
        embeddings_allvar[i]=embeddings[index_all_var[i]]
    print('read and extract end')

    print('read every var and formalparameter for every code')
    data_every_var=pd.read_pickle(root+'/var_for_everyCode_test' + str(mycnt) + '.pkl')
    every_var_list=data_every_var['variable'].tolist()

    #formalParameter
    formalParameter_for_every_code=pd.read_pickle\
        (root+'/data1/java' + str(mycnt) + '/formalParameter_for_everyCode_test.pkl')
    formalParameter_list=formalParameter_for_every_code['variable'].tolist()



    print('select top k nearest var')
    nearest_list=[]
    var_embed=np.zeros((1,embedding_dim))
    count=0


    for every_code in every_var_list:
        nearest_dict={}
        mask_index_list=[]
        formalParameter_every_code =formalParameter_list[count]
        count=count+1
        print('ok'+str(count))
        for var in every_code:
            if var in all_var_list:
                var_index_in_all_var=all_var_list.index(var)
                mask_index_list.append(var_index_in_all_var)


        if formalParameter_every_code!=[]:
            for item in formalParameter_every_code:
                if item in all_var_list:
                    mask_index_list.append(all_var_list.index(item))

        allcan_list=[]
        for var in every_code:
            n_list = []
            var_index=vocab[var] if var in vocab else max_token
            var_embed[0]=embeddings[var_index]
            cos_dist=cosine_similarity(embeddings_allvar,var_embed)
            for item in mask_index_list:
                cos_dist[item][0]=-1

            cos_dist=cos_dist.reshape(max_var)

            k_count=2
            while len(n_list)<k:
                top_k_index=get_topk_index(k_count,cos_dist)
                if (all_var_list[top_k_index[-1]] in allcan_list) ==False:
                    n_list.append(all_var_list[top_k_index[-1]])
                    allcan_list.append(all_var_list[top_k_index[-1]])

                k_count=k_count+1

            nearest_dict[var]=n_list
        nearest_list.append(nearest_dict)



    index=[i for i in range(len(nearest_list))]
    nearest_pd=pd.DataFrame({'id':index,'nearest_k':nearest_list})
    # nearest_pd.to_pickle(root + '/var_name/java' + str(mycnt) + '/code_nearest_top5.pkl')
    nearest_pd.to_pickle(root + '/var_name/java' + str(mycnt) + '/code_nearest_top30.pkl')
    print('end...')
    print(time.strftime(' %Y-%m-%d %H:%M:%S', time.localtime(time.time())))
    end = time.process_time()
    end2 = time.time()
    totaltime += end - start
    totaltime2 += end2 - start2
    print("time cost2: ", end2 - start2)
print("total time2: ", totaltime2)
