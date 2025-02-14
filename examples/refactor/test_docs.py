import os
from uptrain.framework import CheckSet, Settings, Check
from uptrain.operators import (
    Histogram,
    Table,
    BarChart,
    ScatterPlot,
    Distribution,
    CosineSimilarity,
    UMAP,
    JsonReader,
    JsonWriter,
    Embedding,
    RougeScore,
    DocsLinkVersion,
    TextLength,
    TextComparison,
)

# Define the config
LOGS_DIR = "/tmp/uptrain_logs"


# def produce_dataset_w_embs(source_path, sink_path):
#     # Compute all the embeddings - question, document, response

#     source = JsonReader(fpath=source_path)
#     source.setup(Settings())
#     data = source.run()["output"]

#     list_ops = [
#         Embedding(
#             model="MiniLM-L6-v2", col_in_text="question", col_out="question_embeddings"
#         ),
#         Embedding(
#             model="MiniLM-L6-v2",
#             col_in_text="document_text",
#             col_out="context_embeddings",
#         ),
#         Embedding(
#             model="MiniLM-L6-v2", col_in_text="response", col_out="response_embeddings"
#         ),
#     ]
#     for op in list_ops:
#         op.setup(Settings())
#         assert data is not None
#         data = op.run(data)["output"]

#     os.remove(sink_path)
#     JsonWriter(fpath=sink_path).run(data)


def get_list_checks(source_path):
    # Define the config
    checks = []

    checks.append(
        Check(
            name="distribution_of_document_embeddings",
            operators=[
                Distribution(
                    kind="cosine_similarity",
                    col_in_embs=["context_embeddings", "response_embeddings"],
                    col_in_groupby=["question_idx", "experiment_id"],
                    col_out=["similarity-context", "similarity-response"],
                )
            ],
            plots=[
                Histogram(
                    title="Embeddings similarity - Context",
                    x="similarity-context",
                    nbins=20,
                ),
                Histogram(
                    title="Embeddings similarity - Responses",
                    x="similarity-response",
                    nbins=20,
                ),
            ],
        )
    )

    checks.append(
        Check(
            name="text_overlap_between_documents",
            operators=[
                Distribution(
                    kind="rouge",
                    col_in_embs=["document_text"],
                    col_in_groupby=["question_idx", "experiment_id"],
                    col_out=["rouge_f1"],
                )
            ],
            plots=[
                Histogram(
                    title="Text Overlap between document embeddings",
                    x="rouge_f1",
                    nbins=20,
                )
            ],
        )
    )

    checks.append(
        Check(
            name="quality_scores",
            operators=[
                DocsLinkVersion(
                    col_in_text="document_link", col_out="document_link_version"
                ),
                TextLength(
                    col_in_text="document_text", col_out="document_context_length"
                ),
                RougeScore(
                    score_type="f1",
                    col_in_generated="response",
                    col_in_source="document_text",
                    col_out="response_document_overlap_score",
                ),
                CosineSimilarity(
                    col_in_vector_1="question_embeddings",
                    col_in_vector_2="response_embeddings",
                    col_out="question_response_similarity",
                ),
                TextComparison(
                    reference_texts="<EMPTY MESSAGE>",
                    col_in_text="response",
                    col_out="empty_response",
                ),
            ],
            plots=[
                Table(title="Quality scores"),
                BarChart(
                    title="Bar Plot of Link version",
                    x="document_link_version",
                ),
                Histogram(
                    title="Histogram of Context Length",
                    x="document_context_length",
                    nbins=20,
                ),
            ],
        )
    )

    checks.append(
        Check(
            name="question_umap",
            operators=[
                UMAP(
                    col_in_embs_1="question_embeddings",
                    col_in_embs_2="response_embeddings",
                )
            ],
            plots=[
                ScatterPlot(
                    title="UMAP for question embeddings",
                    x="umap_0",
                    y="umap_1",
                    symbol="symbol",
                    color="cluster",
                )
            ],
        )
    )

    return checks


# -----------------------------------------------------------
# Starting a streamlit server to visualize the results
# -----------------------------------------------------------


def start_streamlit():
    from uptrain.dashboard import StreamlitRunner

    runner = StreamlitRunner(LOGS_DIR)
    runner.start()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--start-streamlit", default=False, action="store_true")
    args = parser.parse_args()

    # produce_dataset_w_embs(args.dataset_path, DATASET_W_EMB_PATH)
    DATASET_W_EMB_PATH = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "../datasets/qna_on_docs_samples.jsonl",
    )

    checks = get_list_checks(DATASET_W_EMB_PATH)
    check_set = CheckSet(source=JsonReader(fpath=DATASET_W_EMB_PATH), checks=checks)
    settings = Settings(logs_folder=LOGS_DIR)

    check_set.setup(settings).run()

    if args.start_streamlit:
        start_streamlit()
