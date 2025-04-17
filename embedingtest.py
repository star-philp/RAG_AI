import openai
import pandas as pd
import numpy as np
import os
# from sklearn.decomposition import PCA
# import matplotlib.pyplot as plt

# Set your OpenAI API key
# API 키는 환경 변수에서 가져오거나 직접 설정해야 합니다
# openai.api_key = os.environ.get("OPENAI_API_KEY")

# Define the function to get embeddings using the updated API
def get_embedding(text, model="text-embedding-ada-002"):
    response = openai.Embedding.create(
        input=[text],  # note that input is now a list
        model=model
    )
    return response['data'][0]['embedding']

# Load & inspect dataset
input_datapath = "/Users/rainstar/Downloads/Reviews.csv"
df = pd.read_csv(input_datapath, index_col=0)
df = df[["Time", "ProductId", "UserId", "Score", "Summary", "Text"]]
df = df.dropna()
df["combined"] = (
    "Title: " + df.Summary.str.strip() + "; Content: " + df.Text.str.strip()
)
df.head(2)

# Example: Get embedding for the first row's text
sample_text = df['combined'].iloc[0]
sample_embedding = get_embedding(sample_text)

print(sample_embedding)  # This will print the embedding vector

# print(sample_embedding)

# print(len(sample_embedding))  # This will print the length of the embedding vector

# np.save('sample_embedding.npy', sample_embedding)  # Save the embedding to a file

# pca = PCA(n_components=2)
# reduced_embedding = pca.fit_transform([sample_embedding])

# plt.scatter(reduced_embedding[:, 0], reduced_embedding[:, 1])
# plt.show()