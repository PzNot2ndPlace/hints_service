from collections import defaultdict

import httpx
from fastapi import HTTPException
from typing import Optional, Dict
import statistics

from hints_service.constants import *
from hints_service.schemas import *


class HintsGenerationService:
    def __init__(self):
        if not IAM or not FOLDER_ID:
            print("Warning: IAM or FOLDER_ID not set")
        self.ygpt_url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
        self.ygpt_headers = {
            "Authorization": f"Bearer {IAM}",
            "x-folder-id": FOLDER_ID,
            "Content-Type": "application/json"
        }
        self.time_format = "%Y-%m-%d %H:%M"

    async def generate_time_hint(self, request: TextBasedHintRequest) -> Optional[TextBasedHintResponse]:
        """Генерирует подсказку на основе временных паттернов"""
        time_notes = request.context

        # Анализируем паттерны по категориям
        patterns = self._analyze_time_patterns(time_notes)

        # Создаем подсказку для самой частой категории
        if not patterns:
            return None

        best_category = max(patterns.items(), key=lambda x: x[1]["count"])[0]
        pattern = patterns[best_category]

        # Формируем новую NoteDto для подсказки
        hint = self._build_hint_note(best_category, pattern, request.current_time)

        # Дополнительная обработка через YandexGPT
        # enhanced_hint_text = await self.generate_hint_by_note(hint.note, request.current_time)
        # hint.hintText = enhanced_hint_text

        return hint

    def _analyze_time_patterns(self, notes: List[NoteDto]) -> Dict[CategoryType, Dict]:
        """Выявляет временные паттерны по категориям"""
        patterns = defaultdict(lambda: {"times": [], "count": 0})

        for note in notes:
            for trigger in note.triggers:
                if trigger.triggerType == TriggerType.TIME:
                    try:
                        time = datetime.strptime(trigger.triggerValue, self.time_format).time()
                        patterns[note.categoryType]["times"].append(time)
                        patterns[note.categoryType]["count"] += 1
                    except ValueError:
                        continue

        # Вычисляем среднее время для каждой категории
        for category, data in patterns.items():
            if data["times"]:
                avg_hour = statistics.mean(t.hour for t in data["times"])
                avg_minute = statistics.mean(t.minute for t in data["times"])
                data["avg_time"] = f"{int(avg_hour):02d}:{int(avg_minute):02d}"

        return patterns

    def _build_hint_note(self, category: CategoryType, pattern: Dict, current_time_str: str) -> TextBasedHintResponse:
        """Создает NoteDto с подсказкой"""
        current_time = datetime.strptime(current_time_str, self.time_format)
        avg_time = datetime.strptime(pattern["avg_time"], "%H:%M").time()

        reminder_texts = {
            CategoryType.SHOPPING: "Сделать покупки",
            CategoryType.CALL: "Позвонить",
            CategoryType.HEALTH: "Принять лекарства",
            CategoryType.ROUTINE: "Выполнить рутинное дело"
        }

        hint_texts = {
            CategoryType.SHOPPING: "Вы обычно делаете покупки около {time}",
            CategoryType.CALL: "В это время вы часто звоните {time}",
            CategoryType.HEALTH: "Ваше обычное время для здоровья - {time}",
            CategoryType.ROUTINE: "Обычно вы это делаете около {time}"
        }

        # Рассчитываем разницу времени для подсказки
        trigger_time = current_time.replace(hour=avg_time.hour, minute=avg_time.minute)
        time_diff = trigger_time - current_time
        hours = time_diff.seconds // 3600

        original_reminder_text = reminder_texts.get(category, "Напоминание")
        original_hint_text = hint_texts.get(category, "Рекомендуемое время - {time}").format(time=pattern["avg_time"])

        # Расширенная подсказка с временем
        extended_hint = f"{original_hint_text}. Напомнить через {hours} часов?"

        return TextBasedHintResponse(
            note=NoteDto(
                text=original_reminder_text,
                createdAt=current_time_str,
                updatedAt=None,
                categoryType=category,
                triggers=[TriggerDto(
                    triggerType=TriggerType.TIME,
                    triggerValue=trigger_time.strftime(self.time_format)
                )]
            ),
            hintText=extended_hint
        )

    async def generate_hint_by_note(self, note: NoteDto, current_time) -> str:
        """Постобработка предложенной заметки с помощью API YandexGPT"""

        note_dict = {
            "text": note.text,
            "createdAt": note.createdAt,
            "updatedAt": note.updatedAt,
            "categoryType": note.categoryType,
            "triggers": [{
                "triggerType": t.triggerType,
                "triggerValue": t.triggerValue
            } for t in note.triggers]
        }

        request_data = {
            "modelUri": f"gpt://{FOLDER_ID}/yandexgpt-lite",
            "completionOptions": {
                "stream": False,
                "temperature": 0.1,
                "maxTokens": 1000
            },
            "messages": [
                {
                    "role": "system",
                    "text": self.build_prompt(current_time)
                },
                {
                    "role": "user",
                    "text": f"Ввод: \n{note_dict}"
                }
            ]
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.ygpt_url,
                    headers=self.ygpt_headers,
                    json=request_data
                )
                response.raise_for_status()

                result = response.json()
                llm_output = result['result']['alternatives'][0]['message']['text']

                print(llm_output)

                return llm_output

        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"YandexGPT API error: {e.response.text}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Text processing failed: {str(e)}"
            )

    @staticmethod
    def build_prompt(current_time: str) -> str:
        return f"""
        Ты — AI-ассистент для создания "умных" подсказок. Ты получаешь напоминание в JSON формате, \
        которое нужно предложить пользователю, учитывая его текущее время: {current_time}.
        Возвращай подсказку одним односложным предложением.

        ### Допустимые значения:
        - `categoryType`: Time, Location, Event, Shopping, Call, Meeting, Deadline, Health, Routine, Other  
        - `triggerType`: Time, Location

        ### Правила:
        1. `categoryType` определяется по смыслу напоминания:
           - "купить молоко" → Shopping  
           - "позвонить маме" → Call  
           - "встреча в кафе" → Meeting  
        2. `triggerType` зависит от условия:
           - "в 18:00" → Time 
           - "через 2 часа" → Time
           - "когда буду в Пятёрочке" → Location  
        3. Для относительного времени (e.g., "завтра", "через час") \
        всегда указывай абсолютное время в формате "YYYY-MM-DD HH:MM".

        ### Пример 1 (с текущим временем {current_time} = "2025-06-16 15:00"):
        Ввод: 
        {{
            "text": "Выгулять собаку",
            "categoryType": "Routine",
            "triggers": [
                {{
                    "triggerType": "Time",
                    "triggerValue": "2025-06-16 18:00"
                }}
            ]
        }}
        Вывод:
        Напомнить выгулять собаку через 3 часа?

        ### Пример 2 (с текущим временем {current_time} = "2025-06-16 09:00"):
        Ввод:
        {{
            "text": "Позвонить врачу",
            "categoryType": "Health",
            "triggers": [
                {{
                    "triggerType": "Time",
                    "triggerValue": "2025-06-17 10:00"
                }}
            ]
        }}
        Вывод:
        Напомнить позвонить врачу завтра в 10:00

        Теперь предложи пользователю подсказку для следующего напоминания в формате JSON \
        (текущее время: {current_time}):
        """


hints_generation_service = HintsGenerationService()
