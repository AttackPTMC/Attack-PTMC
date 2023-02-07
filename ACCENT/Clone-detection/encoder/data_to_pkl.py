import pandas as pd

f_code=open('../data1/JAVA/train/code.original_subtoken','r')
f_summ=open('../data1/JAVA/train/javadoc.original','r')

code=[]
summ=[]

for c,s in zip(f_code,f_summ):
    code.append(c)
    summ.append(s)

index_list=[i for i in range(len(code))]

df=pd.DataFrame({'index':index_list,'code':code,'summ':summ})

print(df)
df=df.iloc[0:69696]
df.to_pickle('../Clone-detection/encoder/train_data1.pkl')


