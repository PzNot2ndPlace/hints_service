from collections import defaultdict
from datetime import time, datetime
from typing import Optional, Dict, List
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from hints_service.schemas import *


class HintsGenerationService:
    def __init__(self):
        self.time_format = "%Y-%m-%d %H:%M"
        self.vectorizer = TfidfVectorizer(
            analyzer='word',
            token_pattern=r'\w+',
            min_df=0.1,  # Игнорируем слишком редкие слова
            max_df=0.9  # Игнорируем слишком частые слова
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

        return self._build_hint_from_group(best_group, request.current_time)

    def _group_similar_notes(self, notes: List[NoteDto]) -> Dict[CategoryType, List]:
        """Группировка заметок с использованием TF-IDF"""
        grouped = defaultdict(list)

        # Собираем все тексты для обучения
        if not self._fit_vectorizer:
            all_texts = [n.text for n in notes]
            self.vectorizer.fit(all_texts)
            self._fit_vectorizer = True

        for category in CategoryType:
            category_notes = [n for n in notes if n.categoryType == category]

            if len(category_notes) < 2:
                continue

            # Преобразуем тексты в TF-IDF матрицу
            texts = [n.text for n in category_notes]
            tfidf_matrix = self.vectorizer.transform(texts)

            # Вычисляем матрицу сходства
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

    def _build_hint_from_group(self, group: List[NoteDto], current_time: str) -> TextBasedHintResponse:
        """Создает подсказку на основе группы заметок"""
        time_pattern = self._analyze_group_time_pattern(group)
        category = group[0].categoryType
        reminder_text = group[0].text

        hint_text = (
            f"Вы часто напоминаете себе '{reminder_text}' (найдено {len(group)} похожих напоминаний). "
            f"Обычно вы создаёте такие напоминания около {time_pattern['avg_creation'].strftime('%H:%M')}, "
            f"а срабатывают они в {time_pattern['avg_trigger'].strftime('%H:%M')}."
        )

        trigger_time = datetime.strptime(current_time, self.time_format).replace(
            hour=time_pattern['avg_trigger'].hour,
            minute=time_pattern['avg_trigger'].minute
        )

        return TextBasedHintResponse(
            note=NoteDto(
                text=reminder_text,
                createdAt=current_time,
                updatedAt=None,
                categoryType=category,
                triggers=[TriggerDto(
                    triggerType=TriggerType.TIME,
                    triggerValue=trigger_time.strftime(self.time_format)
                )]
            ),
            hintText=hint_text
        )

    @staticmethod
    def _average_time(times: List[time]) -> time:
        """Вычисляет среднее время из списка"""
        total_seconds = sum(t.hour * 3600 + t.minute * 60 for t in times)
        avg_seconds = total_seconds // len(times)
        return time(hour=avg_seconds // 3600, minute=(avg_seconds % 3600) // 60)


hints_generation_service = HintsGenerationService()
