import lamini
import json
from data import data

lamini.api_key = "d134c446ad7bfeb39e05f3ab41872038a80e0a86889de8c6cc80b8a45e6c3835"

def get_data():
    return data
data = get_data()

llm = lamini.Lamini(model_name='meta-llama/Llama-2-7b-chat-hf')
# llm.data = data
llm.train(data, finetune_args={'learning_rate': 1.0e-7, 'optim' : 'adam'})