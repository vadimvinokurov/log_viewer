<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Кэш текстовых фильтров для мгновенного переключения категорий</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; max-width: 760px; margin: 2em auto; padding: 0 1em; line-height: 1.6; color: #1a1a1a; }
        h1 { border-bottom: 2px solid #e0e0e0; padding-bottom: 0.3em; }
        h2 { margin-top: 1.8em; color: #2c3e50; }
        code { background: #f4f4f4; padding: 0.15em 0.4em; border-radius: 3px; font-size: 0.9em; }
        pre { background: #f4f4f4; padding: 1em; border-radius: 5px; overflow-x: auto; }
        pre code { background: none; padding: 0; }
        ul { padding-left: 1.4em; }
        li { margin-bottom: 0.3em; }
        .label { display: inline-block; padding: 0.1em 0.5em; border-radius: 3px; font-size: 0.85em; font-weight: 600; }
        .label-new { background: #d4edda; color: #155724; }
        .label-modified { background: #fff3cd; color: #856404; }
        .label-unchanged { background: #e2e3e5; color: #383d41; }
    </style>
</head>
<body>

<h1>Кэш текстовых фильтров для мгновенного переключения категорий</h1>

<h2>Проблема</h2>
<p>
    При активных текстовых фильтрах переключение категорий асимметрично по скорости:
</p>
<ul>
    <li><strong>Выключение</strong> категории — мгновенное (меньше строк для обработки).</li>
    <li><strong>Включение</strong> категории — медленное (больше строк для обработки).</li>
</ul>
<p>
    Причина: метод <code>_apply_filters()</code> при каждом переключении вызывает
    <code>_bulk_match()</code>, который заново выполняет дорогое текстовое
    сопоставление (сканирование буфера или декодирование + матчинг каждой строки)
    по всем строкам, прошедшим фильтр категорий.
</p>

<h2>Решение</h2>
<p>
    Кэшировать результат текстовых фильтров в виде boolean-маски NumPy,
    вычисляемой <strong>один раз</strong> при изменении фильтров.
    Переключение категорий/уровней сводится к пересечению NumPy-масок.
</p>

<h2>Дизайн</h2>

<h3>Новый атрибут <span class="label label-new">NEW</span></h3>
<p>
    <code>LogStore._text_filter_mask: np.ndarray</code> — boolean-массив длины n.<br>
    <code>True</code> = строка соответствует хотя бы одному активному текстовому фильтру (логика OR).
</p>

<h3>Новый метод <code>_recompute_text_filter_mask()</code> <span class="label label-new">NEW</span></h3>
<p>
    Выполняет полное текстовое сопоставление для <strong>всех</strong> строк файла
    (не только для строк включённых категорий), используя ту же логику, что и текущий
    <code>_bulk_match</code>:
</p>
<ul>
    <li><strong>Plain-CI</strong>: сканирование буфера через
        <code>combined.finditer(self._buf)</code>, маппинг позиций в индексы строк
        через <code>searchsorted</code>.</li>
    <li><strong>Regex / CS / Simple</strong>: цикл по всем n строкам, декодирование
        сообщения, сопоставление с фильтром.</li>
</ul>
<p>Результат сохраняется в <code>_text_filter_mask</code>.</p>

<h3>Изменённый <code>_apply_filters()</code> <span class="label label-modified">MODIFIED</span></h3>
<p>Вызов <code>_bulk_match</code> заменяется на пересечение масок:</p>
<pre><code># Было:
matched_positions = self._bulk_match(cat_level_list, active_filters)
would_be_visible = cat_level_indices[np.array(sorted(matched_positions), ...)]

# Стало:
if has_text_filters:
    combined = cat_level_mask &amp; self._text_filter_mask
    would_be_visible = np.where(combined)[0].astype(np.uint32)</code></pre>

<h3>Точки инвалидации кэша</h3>
<p><code>_recompute_text_filter_mask()</code> вызывается перед <code>_apply_filters()</code> в:</p>
<ul>
    <li><code>add_filter()</code>, <code>remove_filter()</code>, <code>clear_filters()</code></li>
    <li>Toggle фильтра (enable/disable)</li>
    <li><code>_finalize_load()</code> (после парсинга файла)</li>
</ul>

<h3>Потребление памяти</h3>
<p>
    Один boolean-массив длины n. Для 1&thinsp;000&thinsp;000 строк &asymp; 1&thinsp;МБ. Пренебрежимо мало.
</p>

<h3>Что не меняется <span class="label label-unchanged">UNCHANGED</span></h3>
<ul>
    <li>Метод <code>_bulk_match()</code> сохраняется для использования в <code>store.search()</code>.</li>
    <li>OR-логика фильтров (строка проходит, если соответствует любому фильтру) без изменений.</li>
    <li>API переключения категорий и уровней без изменений.</li>
</ul>

<h2>Верификация</h2>
<ul>
    <li>Существующий набор тестов проходит без изменений поведения.</li>
    <li>Ручная проверка: добавить фильтр на большом файле, переключить категорию &mdash; оба направления мгновенные.</li>
</ul>

</body>
</html>
