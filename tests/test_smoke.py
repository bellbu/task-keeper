from sqlalchemy import event


def test_create_and_list(client):
    res = client.post("/tasks", json={"title": "테스트 할 일", "tags": ["개인", "긴급"]})
    assert res.status_code == 201
    body = res.json()
    assert body["title"] == "테스트 할 일"
    assert {t["name"] for t in body["tags"]} == {"개인", "긴급"}

    res = client.get("/tasks")
    assert res.status_code == 200
    tasks = res.json()
    assert len(tasks) == 1
    assert tasks[0]["tags"]


def test_list_tasks_no_n_plus_one(client, db_session):
    for i in range(5):
        client.post("/tasks", json={"title": f"할 일 {i}", "tags": [f"태그{i}", "공통"]})
    # 세션에 남은 객체 때문에 태그 조회가 생략되지 않도록 비웁니다.
    db_session.expire_all()

    statements = []
    engine = db_session.get_bind()

    def count(conn, cursor, statement, *args):
        if statement.lstrip().upper().startswith("SELECT"):
            statements.append(statement)

    event.listen(engine, "before_cursor_execute", count)
    try:
        res = client.get("/tasks")
    finally:
        event.remove(engine, "before_cursor_execute", count)

    assert res.status_code == 200
    assert len(res.json()) == 5
    # 할 일 개수와 상관없이 할 일 1회 + 태그 1회만 조회해야 합니다.
    assert len(statements) == 2
