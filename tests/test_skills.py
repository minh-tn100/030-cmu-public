import pathlib
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage, HumanMessage
from agent import skills
from agent.skill_agent import build

def _mk(root, name, front=None, body="# body\n"):
    d = root / name; d.mkdir()
    (d / "SKILL.md").write_text(f"---\n{front if front is not None else f'name: {name}' + chr(10) + 'description: does a thing. Use when asked.'}\n---\n{body}", encoding="utf-8")

def test_repo_skill_is_indexed_and_loads():
    assert "designbench-review" in skills.CATALOG
    body = skills.load_skill("designbench-review")
    assert "Never emit gap or ok without a verified cited clause" in body

def test_index_reads_only_frontmatter_and_skips_bad_skills(tmp_path):
    _mk(tmp_path, "good")
    _mk(tmp_path, "mismatch", front="name: other\ndescription: x")          # folder name differs: skipped
    _mk(tmp_path, "nodesc", front="name: nodesc")                           # missing description: skipped
    _mk(tmp_path, "broken", front="name: [unclosed")                        # bad yaml: skipped
    (tmp_path / "empty").mkdir()
    cat = skills.index_skills(tmp_path)
    assert list(cat) == ["good"]

def test_unknown_or_path_names_return_menu_not_files(tmp_path):
    _mk(tmp_path, "good"); cat = skills.index_skills(tmp_path)
    for bad in ("../good", "/etc/passwd", "nope", "", None, 5):
        out = skills.load_skill(bad, cat)
        assert out.startswith("Unknown skill. Available: good")

def test_body_is_capped(tmp_path):
    _mk(tmp_path, "big", body="x" * 50_000); cat = skills.index_skills(tmp_path)
    assert len(skills.load_skill("big", cat)) == skills.MAX_BODY

class _Fake(FakeMessagesListChatModel):
    def bind_tools(self, tools, **kw): return self

def test_graph_loads_skill_then_answers():
    msgs = [AIMessage(content="", tool_calls=[{"name": "load_skill", "args": {"name": "designbench-review"}, "id": "c1"}]),
            AIMessage(content="Run the offline review first.")]
    app = build(_Fake(responses=msgs))
    out = app.invoke({"messages": [HumanMessage("review the Bank X design")]})
    tool_msg = [m for m in out["messages"] if m.type == "tool"][0]
    assert "Never emit gap or ok" in tool_msg.content and out["messages"][-1].content.startswith("Run the offline")
