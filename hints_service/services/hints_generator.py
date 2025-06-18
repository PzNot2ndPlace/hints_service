from collections import defaultdict
from datetime import time
from typing import Dict

import httpx
import numpy as np
from fastapi import HTTPException
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from hints_service.schemas import *
from hints_service.constants import *


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
        self.vectorizer = TfidfVectorizer(
            analyzer='word',
            token_pattern=r'\w+',
            min_df=0.1,
            max_df=0.9
        )
        self.similarity_threshold = 0.7  # Порог для группировки заметок
        self._fit_vectorizer = False

    async def generate_time_hint(self, request: TextBasedHintRequest) -> Optional[TextBasedHintResponse]:
        """Генерация подсказки на основе временных паттернов"""
        time_notes = request.context

        if not time_notes:
            return None

        grouped_notes = self._group_similar_notes(time_notes)
        best_group = self._find_best_recommendation(grouped_notes, request.current_time)

        if not best_group:
            return None

        return await self._build_hint_from_group(best_group, request.current_time)

    def _group_similar_notes(self, notes: List[NoteDto]) -> Dict[CategoryType, List]:
        """Группировка заметок с использованием TF-IDF"""
        grouped = defaultdict(list)

        # Собираем все тексты для "обучения" TF-IDF
        if not self._fit_vectorizer:
            all_texts = [n.text for n in notes]
            self.vectorizer.fit(all_texts)
            self._fit_vectorizer = True

        for category in CategoryType:
            category_notes = [n for n in notes if n.categoryType == category]

            # Скипаем категории в которых мало заметок
            if len(category_notes) < 2:
                continue

            # Преобразуем тексты в TF-IDF матрицу
            texts = [n.text for n in category_notes]
            tfidf_matrix = self.vectorizer.transform(texts)

            # Считаем косинусное сходство (матрицу)
            sim_matrix = cosine_similarity(tfidf_matrix)

            # Группируем похожие заметки
            groups = []
            used_indices = set()

            for i in range(len(category_notes)):
                if i not in used_indices:
                    similar_indices = np.where(sim_matrix[i] > self.similarity_threshold)[0]
                    group = [category_notes[j] for j in similar_indices]
                    groups.append(group)
                    used_indices.update(similar_indices)

            grouped[category] = groups

        return grouped

    def _find_best_recommendation(self, grouped_notes: Dict[CategoryType, List], current_time: str) -> Optional[List]:
        """Выбирает лучшую группу для рекомендации"""
        current_dt = datetime.strptime(current_time, self.time_format)
        best_group = None
        best_score = 0

        for category, groups in grouped_notes.items():
            for group in groups:
                if len(group) < 2:
                    continue

                time_pattern = self._analyze_group_time_pattern(group)
                score = self._calculate_group_score(time_pattern, current_dt)

                if score > best_score:
                    best_score = score
                    best_group = group

        return best_group

    def _analyze_group_time_pattern(self, group: List[NoteDto]) -> Dict:
        """Анализирует временные паттерны группы заметок"""
        trigger_times = []
        creation_times = []

        for note in group:
            for trigger in note.triggers:
                if trigger.triggerType == TriggerType.TIME:
                    trigger_times.append(datetime.strptime(trigger.triggerValue, self.time_format))

            creation_times.append(datetime.strptime(note.createdAt, self.time_format))

        avg_trigger = self._average_time([t.time() for t in trigger_times])
        avg_creation = self._average_time([t.time() for t in creation_times])

        return {
            'avg_trigger': avg_trigger,
            'avg_creation': avg_creation,
            'count': len(group)
        }

    def _calculate_group_score(self, time_pattern: Dict, current_dt: datetime) -> float:
        """Вычисляет релевантность группы для текущего времени"""
        current_time = current_dt.time()
        avg_creation = time_pattern['avg_creation']

        time_diff = (current_dt - datetime.combine(current_dt.date(), avg_creation)).total_seconds() / 3600
        time_factor = max(0, 1 - abs(time_diff) / 12)
        count_factor = min(1, time_pattern['count'] / 5)

        return time_factor * count_factor

    async def _build_hint_from_group(self, group: List[NoteDto], current_time: str) -> TextBasedHintResponse:
        """Создает подсказку на основе группы заметок"""
        time_pattern = self._analyze_group_time_pattern(group)
        category = group[0].categoryType
        reminder_text = group[0].text
        current_dt = datetime.strptime(current_time, self.time_format)

        # Вычисляем рекомендуемое время триггера
        trigger_time = current_dt.replace(
            hour=time_pattern['avg_trigger'].hour,
            minute=time_pattern['avg_trigger'].minute
        )

        # Если триггерное время уже прошло, переносим на следующий день
        if trigger_time <= current_dt:
            trigger_time = trigger_time.replace(day=trigger_time.day + 1)

        hint_note = NoteDto(
            text=reminder_text,
            createdAt=current_time,
            updatedAt=None,
            categoryType=category,
            triggers=[TriggerDto(
                triggerType=TriggerType.TIME,
                triggerValue=trigger_time.strftime(self.time_format)
            )]
        )

        # Добавляем await перед вызовом асинхронного метода
        hint_text = await self.generate_hint_by_note(hint_note, current_time)

        return TextBasedHintResponse(
            note=hint_note,
            hintText=hint_text
        )

    @staticmethod
    def _average_time(times: List[time]) -> time:
        """Вычисляет среднее время из списка"""
        total_seconds = sum(t.hour * 3600 + t.minute * 60 for t in times)
        avg_seconds = total_seconds // len(times)
        return time(hour=avg_seconds // 3600, minute=(avg_seconds % 3600) // 60)

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
