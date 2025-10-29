import asyncio, json
from fastapi import HTTPException
from fastapi.concurrency import run_in_threadpool
from google.genai import types
from config import client, MODEL_ID
from models.schemas import AgentRecommendationList, RecommendationList, BookRecommendation
from services.cover_service import lookup_cover

async def get_recommendations_from_ai(prompt: str) -> RecommendationList:
    """
    Generates structured book recommendations from AI and fetches cover URLs.
    """
    system_instruction = (
        "You are a helpful and creative book recommendation agent. "
        "Provide exactly 3 distinct book recommendations based on the user's prompt. "
        "Include the exact title and author for each book. "
        "**DO NOT** include cover URLs. The response must strictly match the given JSON schema."
    )

    agent_schema_dict = AgentRecommendationList.model_json_schema()

    try:
        response = await run_in_threadpool(
            client.models.generate_content,
            model=MODEL_ID,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=agent_schema_dict,
            )
        )

        agent_result = AgentRecommendationList.model_validate(json.loads(response.text))

        cover_tasks = [
            run_in_threadpool(lookup_cover, title=item.title, author=item.author)
            for item in agent_result.recommendations
        ]
        cover_urls = await asyncio.gather(*cover_tasks)

        final_recommendations = [
            BookRecommendation(
                title=item.title,
                author=item.author,
                reasoning=item.reasoning,
                cover_url=url
            )
            for item, url in zip(agent_result.recommendations, cover_urls)
        ]

        return RecommendationList(recommendations=final_recommendations)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating recommendations: {e}")
