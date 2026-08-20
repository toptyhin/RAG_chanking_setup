/** Demo corpus + golden labels for a first retrieval evaluation. */

export const SAMPLE_CHUNKS = {
  chunks: [
    {
      chunk_id: "c_return",
      doc_id: "policy",
      text: "Customers may return unused items within 30 days of delivery for a full refund.",
    },
    {
      chunk_id: "c_shipping",
      doc_id: "policy",
      text: "Standard shipping takes 3–5 business days. Express ships overnight.",
    },
    {
      chunk_id: "c_warranty",
      doc_id: "policy",
      text: "All electronics include a one-year limited warranty covering manufacturing defects.",
    },
    {
      chunk_id: "c_support",
      doc_id: "support",
      text: "Contact support at help@example.com or chat weekdays 9am–6pm ET.",
    },
  ],
};

export function sampleTestSet(chunkSetId: string) {
  return {
    chunk_set_id: chunkSetId,
    queries: [
      {
        text: "How long do I have to return a product?",
        relevant_chunk_ids: ["c_return"],
      },
      {
        text: "What is the warranty on electronics?",
        relevant_chunk_ids: ["c_warranty"],
      },
      {
        text: "How can I contact customer support?",
        relevant_chunk_ids: ["c_support"],
      },
    ],
  };
}
