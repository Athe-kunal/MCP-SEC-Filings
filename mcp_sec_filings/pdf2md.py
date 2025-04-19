import os
import asyncio
import pdf2image
import pathlib
from loguru import logger
from vllm import LLM, SamplingParams
from mcp_sec_filings import constants, datamodels, docling_vllm

async def convert_single_pdf_to_markdown(semaphore: asyncio.Semaphore, mcpresult_pdf: datamodels.MCPResultsPDF, llm: LLM, sampling_params: SamplingParams):
    images = pdf2image.convert_from_path(mcpresult_pdf.pdf_path)
    tasks = [
        docling_vllm.convert_single_image_to_md(semaphore, llm, sampling_params, image)
        for image in images
    ]
    md_list = await asyncio.gather(*tasks)
    concatenated_md = constants.PAGE_BREAK.join(md_list)
    stem_name = pathlib.Path(mcpresult_pdf.pdf_path).stem
    with open(f"{stem_name}.md", "w", encoding="utf-8") as f:
        f.write(concatenated_md)
        logger.info(f"Saved markdown for {mcpresult_pdf.model_dump()} at {f.name}")

def convert_pdf_list_to_markdown(semaphore: asyncio.Semaphore, mcpresult_pdf_list: list[datamodels.MCPResultsPDF], llm: LLM, sampling_params: SamplingParams):
    tasks = [
        convert_single_pdf_to_markdown(semaphore, mcpresult_pdf, llm, sampling_params)
        for mcpresult_pdf in mcpresult_pdf_list
    ]
    return asyncio.gather(*tasks)

def pdf2md_main(mcpresult_pdf_list: list[datamodels.MCPResultsPDF]):
    max_concurrency = os.getenv("MAX_CONCURRENCY", 2)
    semaphore = asyncio.Semaphore(max_concurrency)
    llm, sampling_params = docling_vllm.load_vllm_model()
    tasks = convert_pdf_list_to_markdown(semaphore, mcpresult_pdf_list, llm, sampling_params)
    return asyncio.run(tasks)

