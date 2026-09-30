from app.memo_store import MemoStore


def test_create_save_and_load_memo(tmp_path) -> None:
    store = MemoStore(tmp_path)

    memo = store.create(
        "API 메모",
        "## 확인\n\n- 첫 번째\n- 두 번째\n",
    )
    loaded = store.load(memo.memo_id)

    assert loaded.title == "API 메모"
    assert loaded.content == "## 확인\n\n- 첫 번째\n- 두 번째\n"
    assert store.path_for(memo.memo_id).suffix == ".md"


def test_title_change_keeps_same_memo_file(tmp_path) -> None:
    store = MemoStore(tmp_path)
    memo = store.create("처음 제목", "본문")

    saved = store.save(memo.memo_id, "바뀐 제목", "본문 수정")

    assert saved.memo_id == memo.memo_id
    assert store.load(memo.memo_id).title == "바뀐 제목"
    assert len(list(tmp_path.glob("*.md"))) == 1


def test_memo_search_finds_title_and_markdown_body(tmp_path) -> None:
    store = MemoStore(tmp_path)
    first = store.create("Kafka 정리", "consumer 설정")
    second = store.create("일반 메모", "## Redis\n\n캐시 삭제")

    title_results = store.search("kafka")
    body_results = store.search("redis")

    assert [item.memo_id for item in title_results] == [first.memo_id]
    assert [item.memo_id for item in body_results] == [second.memo_id]
    assert body_results[0].snippet == "## Redis"


def test_delete_memo(tmp_path) -> None:
    store = MemoStore(tmp_path)
    memo = store.create("삭제", "")

    store.delete(memo.memo_id)

    assert not store.path_for(memo.memo_id).exists()


def test_parse_legacy_plain_markdown_without_title(tmp_path) -> None:
    store = MemoStore(tmp_path)
    path = tmp_path / "legacy.md"
    path.write_text("## 내용\n\n- 항목\n", encoding="utf-8")

    memo = store.load("legacy")

    assert memo.title == "legacy"
    assert memo.content == "## 내용\n\n- 항목\n"



def test_memo_order_is_persisted(tmp_path) -> None:
    store = MemoStore(tmp_path)
    first = store.create("첫 번째", "")
    second = store.create("두 번째", "")
    third = store.create("세 번째", "")

    store.reorder([third.memo_id, first.memo_id, second.memo_id])

    reloaded = MemoStore(tmp_path)
    assert [memo.memo_id for memo in reloaded.list_memos()] == [
        third.memo_id,
        first.memo_id,
        second.memo_id,
    ]


def test_new_memo_is_appended_after_custom_order(tmp_path) -> None:
    store = MemoStore(tmp_path)
    first = store.create("첫 번째", "")
    second = store.create("두 번째", "")
    store.reorder([second.memo_id, first.memo_id])

    third = store.create("세 번째", "")

    assert [memo.memo_id for memo in store.list_memos()] == [
        second.memo_id,
        first.memo_id,
        third.memo_id,
    ]


def test_delete_memo_removes_it_from_saved_order(tmp_path) -> None:
    store = MemoStore(tmp_path)
    first = store.create("첫 번째", "")
    second = store.create("두 번째", "")
    store.reorder([second.memo_id, first.memo_id])

    store.delete(second.memo_id)

    assert [memo.memo_id for memo in MemoStore(tmp_path).list_memos()] == [
        first.memo_id
    ]
