from app.pipelines.transformers.text import normalize_column_name, normalize_text


def test_normalize_text_removes_accents_and_extra_spaces() -> None:
    assert normalize_text("  São   Paulo  ") == "sao paulo"


def test_normalize_text_preserves_none() -> None:
    assert normalize_text(None) is None


def test_normalize_column_name() -> None:
    assert normalize_column_name("Data de Competência") == "data_de_competencia"
