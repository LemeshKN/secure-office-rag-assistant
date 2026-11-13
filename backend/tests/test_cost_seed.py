from app.cost.budgets import find_budget
from app.cost.seed import seed_cost_data
from app.models import Budget, Project, ProjectMember, User, UserProfile


def counts(db) -> tuple[int, int, int, int]:
    return (
        db.query(Budget).count(),
        db.query(Project).count(),
        db.query(ProjectMember).count(),
        db.query(UserProfile).count(),
    )


def test_seed_assigns_departments(seeded_db) -> None:
    departments = {
        user.username: seeded_db.get(UserProfile, user.id).department
        for user in seeded_db.query(User).all()
    }
    assert departments == {
        "admin": "Platform",
        "lemesh": "Engineering",
        "priya": "Engineering",
        "amit": "Engineering",
        "khushi": "HR",
    }


def test_seed_is_idempotent(seeded_db) -> None:
    assert counts(seeded_db) == (12, 4, 7, 5)
    seed_cost_data(seeded_db)
    assert counts(seeded_db) == (12, 4, 7, 5)


def test_seed_budget_amounts(seeded_db) -> None:
    priya = seeded_db.query(User).filter(User.username == "priya").one()
    apollo = seeded_db.query(Project).filter(Project.name == "Apollo").one()
    assert find_budget(seeded_db, "user", str(priya.id)).budget_amount == 0.03
    assert find_budget(seeded_db, "department", "Engineering").budget_amount == 0.30
    assert find_budget(seeded_db, "project", str(apollo.id)).budget_amount == 0.15


def test_me_returns_department_projects_and_budgets(cost_client, auth_headers) -> None:
    response = cost_client.get("/cost/me", headers=auth_headers("priya"))
    assert response.status_code == 200
    body = response.json()
    assert body["department"] == "Engineering"
    assert body["user_budget"]["budget_amount"] == 0.03
    assert body["user_budget"]["remaining_amount"] == 0.03
    assert body["department_budget"]["budget_amount"] == 0.30
    assert [project["name"] for project in body["projects"]] == ["Apollo", "Internal Tools"]


def test_me_lists_only_own_projects(cost_client, auth_headers) -> None:
    body = cost_client.get("/cost/me", headers=auth_headers("khushi")).json()
    assert body["department"] == "HR"
    assert [project["name"] for project in body["projects"]] == ["HR Onboarding"]


def test_me_requires_login(cost_client) -> None:
    assert cost_client.get("/cost/me").status_code == 401