"""Документы целиком в каждом запросе: модель видит общий контекст, а не выдержки по теме."""
from tests.support import files


def _big_doc(tmp_path, lines=1500):
    body = '\n'.join(f'Раздел {i}. Справочная строка номер {i} о системе' for i in range(lines))
    return files.write(tmp_path / 'полный.md', 'НАЧАЛО-ДОКУМЕНТА\n' + body + '\nКОНЕЦ-ДОКУМЕНТА')


def test_every_stage_gets_the_whole_document(app, tmp_path):
    app.upload(_big_doc(tmp_path))
    app.generate()
    for name in ('promptChecklist', 'promptPlan', 'promptGenerate', 'promptReviewCases'):
        ps = app.model.prompts_of(name)
        if not ps:
            continue
        p = ps[-1]
        assert 'НАЧАЛО-ДОКУМЕНТА' in p and 'КОНЕЦ-ДОКУМЕНТА' in p, name
        assert '## Фрагменты исходных документов' not in p, name
    assert app.model.prompts_of('promptGenerate'), 'генерация не вызывалась'


def test_document_text_is_in_the_cached_part_of_generation(app, tmp_path):
    app.upload(_big_doc(tmp_path))
    app.generate()
    p = app.model.prompts_of('promptGenerate')[-1]
    assert p.index('КОНЕЦ-ДОКУМЕНТА') < p.index('## Что покрыть')   # полный текст до границы кэша — одинаков во всех пакетах


def test_each_analysis_fragment_sees_all_documents(app, tmp_path):
    app.upload(_big_doc(tmp_path, 2500))   # ~110 тыс. знаков: несколько фрагментов анализа
    app.generate()
    ps = app.model.prompts_of('promptAnalyze')
    assert len(ps) > 1
    for p in ps:
        assert 'НАЧАЛО-ДОКУМЕНТА' in p and 'КОНЕЦ-ДОКУМЕНТА' in p
        assert 'Требования выделяй только из этого фрагмента' in p
