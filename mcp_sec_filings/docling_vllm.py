import asyncio
import torch
from docling_core.types.doc import DoclingDocument
from docling_core.types.doc.document import DocTagsDocument
from transformers import AutoProcessor, AutoModelForVision2Seq
from vllm import AsyncLLMEngine, SamplingParams
from vllm.engine.arg_utils import AsyncEngineArgs
from PIL import Image

from mcp_sec_filings import constants


def load_model()-> tuple[AutoProcessor, AutoModelForVision2Seq]:
    device = "cuda" if torch.cuda.is_available() else "cpu"
    processor = AutoProcessor.from_pretrained(constants.DOCLING_MODEL_NAME)
    model = AutoModelForVision2Seq.from_pretrained(
        constants.DOCLING_MODEL_NAME,
        torch_dtype=torch.bfloat16,
        # _attn_implementation="flash_attention_2" if DEVICE == "cuda" else "eager",
    ).to(device)

    return processor, model

def load_vllm_model():
    llm = AsyncLLMEngine.from_engine_args(
        AsyncEngineArgs(
            model = constants.DOCLING_MODEL_NAME,
            dtype="auto",
            enforce_eager=True,
            gpu_memory_utilization=0.9,
            disable_log_requests=True
        )
    )

    sampling_params = SamplingParams(
        temperature=0.0,
        max_tokens=constants.MAX_TOKENS)
    return llm, sampling_params

async def convert_single_image_to_md(sempahore:asyncio.Semaphore, llm: AsyncLLMEngine, sampling_params: SamplingParams, image: Image.Image)-> str | None:
    try:
        async with sempahore:
            llm_input = {"prompt": constants.CHAT_TEMPLATE, "multi_modal_data": {"image": image}}
            output = await llm.generate([llm_input], sampling_params=sampling_params)[0]
            doctags = output.outputs[0].text
            doctags_doc = DocTagsDocument.from_doctags_and_image_pairs([doctags], [image])
            doc = DoclingDocument(name="Document")
            doc.load_from_doctags(doctags_doc)
            return doc.export_to_markdown()
    except Exception as e:
        return None

