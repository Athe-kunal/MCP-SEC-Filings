import os
import asyncio
import pdf2image
import pathlib
from loguru import logger
from vllm import AsyncLLMEngine, SamplingParams
from mcp_sec_filings import constants, datamodels, docling_vllm

async def convert_single_pdf_to_markdown(semaphore: asyncio.Semaphore, mcpresult_pdf: datamodels.MCPResultsPDF, llm: AsyncLLMEngine, sampling_params: SamplingParams):
    images = pdf2image.convert_from_path(mcpresult_pdf.pdf_path)
    tasks = [
        docling_vllm.convert_single_image_to_md(semaphore, llm, sampling_params, image)
        for image in images
    ]
    md_list = await asyncio.gather(*tasks, return_exceptions=True)
    md_ist_str: list[str] = []
    for ml in md_list:
        if isinstance(ml, Exception):
            logger.error(f"Failed to convert {mcpresult_pdf.model_dump()} with error {ml}")
        else:
            md_ist_str.append(ml)
    concatenated_md = constants.PAGE_BREAK.join(md_list)
    pdf_path = pathlib.Path(mcpresult_pdf.pdf_path)
    md_path = pdf_path.with_suffix(".md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(concatenated_md)
        logger.info(f"Saved markdown for {mcpresult_pdf.model_dump()} at {f.name}")

async def convert_pdf_list_to_markdown(semaphore: asyncio.Semaphore, mcpresult_pdf_list: list[datamodels.MCPResultsPDF], llm: AsyncLLMEngine, sampling_params: SamplingParams):
    tasks = [
        convert_single_pdf_to_markdown(semaphore, mcpresult_pdf, llm, sampling_params)
        for mcpresult_pdf in mcpresult_pdf_list
    ]
    return asyncio.gather(*tasks, return_exceptions=True)

async def pdf2md_main(mcpresult_pdf_list: list[datamodels.MCPResultsPDF]):
    max_concurrency = int(os.getenv("MAX_CONCURRENCY", "2"))
    semaphore = asyncio.Semaphore(max_concurrency)
    llm, sampling_params = docling_vllm.load_vllm_model()
    return await convert_pdf_list_to_markdown(semaphore, mcpresult_pdf_list, llm, sampling_params)

