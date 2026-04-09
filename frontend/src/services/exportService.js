import client from "./apiClient";

const triggerBlobDownload = (data, filename, mimeType) => {
  const blob = new Blob([data], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
};

export const downloadScanExport = async (scanId, format) => {
  const response = await client.get(`/api/export/${scanId}/${format}`, {
    responseType: format === "pdf" ? "blob" : "text",
  });

  const fileMap = {
    pdf: { name: `scan-${scanId}.pdf`, type: "application/pdf" },
    json: { name: `scan-${scanId}.json`, type: "application/json" },
    csv: { name: `scan-${scanId}.csv`, type: "text/csv" },
    md: { name: `scan-${scanId}.md`, type: "text/markdown" },
  };

  const target = fileMap[format] || fileMap.json;
  triggerBlobDownload(response.data, target.name, target.type);
};
