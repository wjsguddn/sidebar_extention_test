export async function documentCollector(pdfUrl) {
  console.log('PDF 수집 시작:', pdfUrl);
  const response = await fetch(pdfUrl);
  const blob = await response.blob();
  console.log('Blob 생성 완료:', blob.size, 'bytes');
  return blob;
}