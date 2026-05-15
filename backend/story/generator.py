import os
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

DASHSCOPE_API_KEY = os.environ.get("DASHSCOPE_API_KEY", "sk-placeholder-key")
MODEL = "qwen-plus"


def build_prompt(photos: list, metadata: dict, template: str = "timeline", title: str = "", custom_prompt: str = "") -> str:
    photo_filenames = [p.get("path", "").split("/")[-1] for p in photos]
    
    template_instructions = {
        "timeline": "按时间顺序组织章节，展现旅程的起承转合",
        "grid": "按主题分组照片，如风景、人物、美食等",
        "story": "构建一个有起承转合的叙事结构，像讲故事一样"
    }
    
    template_desc = template_instructions.get(template, template_instructions["timeline"])
    
    prompt = f"""You are a professional photo album narrator. Given a collection of photos and their analysis metadata, generate a compelling narrative story.

PHOTO LIST:
{json.dumps(photo_filenames, ensure_ascii=False, indent=2)}

METADATA:
{json.dumps(metadata, ensure_ascii=False, indent=2)}

TEMPLATE: {template}
{template_desc}

OUTPUT FORMAT (JSON only, no markdown formatting):
{{
  "title": "Album title in Chinese or appropriate language",
  "narrative": [
    {{
      "chapter": 1,
      "title": "Chapter title",
      "summary": "Brief summary of this chapter",
      "photos": ["filename1.jpg", "filename2.jpg"],
      "story": "Detailed narrative for this chapter"
    }}
  ],
  "layout": "{template}"
}}

REQUIREMENTS:
1. Output ONLY valid JSON, no markdown code blocks, no extra text
2. Use photos from the photo list above
3. Each chapter should reference 2-5 photos by filename
4. The narrative should be engaging and emotionally resonant
5. Match the tone and style to the template type
6. Keep stories concise but vivid
"""
    
    if title:
        prompt = f"SUGGESTED TITLE: {title}\n\n" + prompt
    
    if custom_prompt:
        prompt = f"\nADDITIONAL INSTRUCTIONS: {custom_prompt}\n" + prompt
    
    return prompt


def _call_qwen_api(prompt: str) -> Optional[str]:
    if DASHSCOPE_API_KEY == "sk-placeholder-key":
        logger.warning("Using placeholder API key, returning mock story")
        return None
    
    try:
        import dashscope
        from http import HTTPStatus
        
        dashscope.api_key = DASHSCOPE_API_KEY
        
        response = dashscope.Generation.call(
            model=MODEL,
            prompt=prompt,
            result_format='message',
        )
        
        if response.status_code == HTTPStatus.OK:
            return response.output.choices[0].message.content
        else:
            logger.warning(f"Qwen API error: {response.code} - {response.message}")
            return None
            
    except Exception as e:
        logger.warning(f"Qwen API call failed: {e}")
        return None


def _create_mock_story(photos: list, template: str, title: str) -> dict:
    return {
        "title": title or "Photo Story",
        "narrative": [{
            "chapter": 1,
            "title": "美好回忆",
            "summary": "这是一段美好的旅程",
            "photos": [p.get("filename", p.get("path", "").split("/")[-1]) for p in photos[:5]],
            "story": "这些照片记录了美好的瞬间。每个瞬间都是一段回忆。"
        }],
        "layout": template
    }


def generate_story(photos: list, metadata: dict, template: str = "timeline", title: str = "", custom_prompt: str = "") -> dict:
    prompt = build_prompt(photos, metadata, template, title, custom_prompt)
    
    response_text = _call_qwen_api(prompt)
    
    if response_text is None:
        logger.warning("API returned no response, using mock story")
        return _create_mock_story(photos, template, title)
    
    try:
        response_text = response_text.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()
        
        story = json.loads(response_text)
        return story
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Qwen response as JSON: {e}")
        return _create_mock_story(photos, template, title)


async def generate_story_async(task_id: str, photos: list, metadata: dict, template: str, title: str, custom_prompt: str, state_update_fn, ws_manager) -> None:
    try:
        await state_update_fn(task_id, "running", 10)
        
        story = generate_story(photos, metadata, template, title, custom_prompt)
        
        await state_update_fn(task_id, "running", 90)
        
        await state_update_fn(task_id, "completed", 100, result=story)
        
        if ws_manager:
            await ws_manager.broadcast(task_id, {"type": "story_completed", "story": story})
        
        logger.info(f"Story generation task {task_id} completed")
        
    except Exception as e:
        logger.error(f"Story generation task {task_id} failed: {e}")
        
        await state_update_fn(task_id, "failed", 0, error=str(e))
        
        if ws_manager:
            await ws_manager.broadcast(task_id, {"type": "story_failed", "error": str(e)})
