### How to:
```
  docker-compose up --build
```

### API docs
```
  http://localhost:8000/docs
```

### Example
Input:
```json
{
  "context": [
    {
      "text": "Купить молоко",
      "createdAt": "2025-06-11 09:00",
      "updatedAt": "2025-06-11 09:00",
      "categoryType": "Shopping",
      "triggers": [
        {
          "triggerType": "Time",
          "triggerValue": "2025-06-11 18:30"
        }
      ]
    },
    {
      "text": "Принять таблетки",
      "createdAt": "2025-06-12 00:30",
      "updatedAt": "2025-06-12 00:30",
      "categoryType": "Health",
      "triggers": [
        {
          "triggerType": "Time",
          "triggerValue": "2025-06-12 09:00"
        }
      ]
    },
    {
      "text": "Забрать ребенка из школы",
      "createdAt": "2025-06-13 12:00",
      "updatedAt": "2025-06-13 12:00",
      "categoryType": "Routine",
      "triggers": [
        {
          "triggerType": "Time",
          "triggerValue": "2025-06-13 15:30"
        }
      ]
    },
    {
      "text": "Встреча с другом",
      "createdAt": "2025-06-15 14:00",
      "updatedAt": "2025-06-15 14:00",
      "categoryType": "Meeting",
      "triggers": [
        {
          "triggerType": "Time",
          "triggerValue": "2025-06-15 17:00"
        }
      ]
    },
    {
      "text": "Заказать пиццу",
      "createdAt": "2025-06-16 16:00",
      "updatedAt": "2025-06-16 16:00",
      "categoryType": "Shopping",
      "triggers": [
        {
          "triggerType": "Time",
          "triggerValue": "2025-06-16 19:30"
        }
      ]
    },
    {
      "text": "Йога",
      "createdAt": "2025-06-17 22:00",
      "updatedAt": "2025-06-17 22:00",
      "categoryType": "Health",
      "triggers": [
        {
          "triggerType": "Time",
          "triggerValue": "2025-06-18 07:30"
        }
      ]
    },
    {
      "text": "Купить подарок",
      "createdAt": "2025-06-21 11:00",
      "updatedAt": "2025-06-21 11:00",
      "categoryType": "Shopping",
      "triggers": [
        {
          "triggerType": "Time",
          "triggerValue": "2025-06-21 16:00"
        }
      ]
    },
    {
      "text": "Позвонить бабушке",
      "createdAt": "2025-06-22 18:00",
      "updatedAt": "2025-06-22 18:00",
      "categoryType": "Call",
      "triggers": [
        {
          "triggerType": "Time",
          "triggerValue": "2025-06-22 19:30"
        }
      ]
    },
    {
      "text": "Сдать отчет",
      "createdAt": "2025-06-23 09:00",
      "updatedAt": "2025-06-23 09:00",
      "categoryType": "Deadline",
      "triggers": [
        {
          "triggerType": "Time",
          "triggerValue": "2025-06-23 17:00"
        }
      ]
    },
    {
      "text": "Отчет по работе",
      "createdAt": "2025-06-25 09:23",
      "updatedAt": "2025-06-25 09:23",
      "categoryType": "Deadline",
      "triggers": [
        {
          "triggerType": "Time",
          "triggerValue": "2025-06-23 17:00"
        }
      ]
    },
    {
      "text": "Сделать отчет",
      "createdAt": "2025-06-27 10:17",
      "updatedAt": "2025-06-27 10:17",
      "categoryType": "Deadline",
      "triggers": [
        {
          "triggerType": "Time",
          "triggerValue": "2025-06-23 18:00"
        }
      ]
    }
  ],
  "current_time": "2025-06-25 10:00"
}
```

Output:
```json
{
  "note": {
    "text": "Сделать покупки",
    "createdAt": "2025-06-25 10:00",
    "updatedAt": null,
    "categoryType": "Shopping",
    "triggers": [
      {
        "triggerType": "Time",
        "triggerValue": "2025-06-25 17:20"
      }
    ]
  },
  "hintText": "Вы обычно делаете покупки около 17:20. Напомнить через 7 часов?"
}
```
