import openai
import pandas as pd
import numpy as np
import os
from sklearn.decomposition import PCA
import matplotlib.pyplot as plt

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

# Example: Get embeddings for the first few rows' text
embeddings = []
for text in df['combined'].head(10):  # Adjust the number of samples as needed
    embedding = get_embedding(text)
    embeddings.append(embedding)

embeddings = np.array(embeddings)

print("Embeddings shape:", embeddings.shape)  # Check the shape of the array

pca = PCA(n_components=2)
reduced_embeddings = pca.fit_transform(embeddings)

plt.scatter(reduced_embeddings[:, 0], reduced_embeddings[:, 1])
plt.xlabel('PCA Component 1')
plt.ylabel('PCA Component 2')
plt.title('PCA of Embeddings')
plt.show()
