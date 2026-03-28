from app.services.legal_analyst_step_llm_service import call_legal_step_llm


class LegalAnalystStepChatService:
    def reply(
        self,
        *,
        step_id: str,
        user_message: str,
        goal_type: str | None = None,
        document_id: str | None = None,
        filename: str | None = None,
        step_output: dict | None = None,
    ) -> dict:
        result = call_legal_step_llm(
            step_id=step_id,
            user_message=user_message,
            goal_type=goal_type,
            document_id=document_id,
            filename=filename,
            step_output=step_output or {},
        )

        reply = result.get("reply", "No pude responder en este paso.")
        render_blocks = result.get("render_blocks", [])

        if not isinstance(render_blocks, list):
            render_blocks = []

        return {
            "step_id": step_id,
            "reply": reply,
            "render_blocks": render_blocks,
        }