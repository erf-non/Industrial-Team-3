import lamini

lamini.api_key = "d134c446ad7bfeb39e05f3ab41872038a80e0a86889de8c6cc80b8a45e6c3835"

ModleID = "9654f488cc4f9246e68e647654b8138f983ae8de28a041ecd66041c825ecb2d0"
with open(r"D:\CCW\Python\LLM\abc.txt", 'r', encoding= 'utf-8') as p:
    prompt = p.read()

Q = \
'''
A 品牌 無線充電器這款充電器的用途是什麼？
'''
input_ =  Q
my_output = lamini.Lamini(model_name= ModleID)
print(my_output.generate(input_))