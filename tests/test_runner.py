from aiforge.runner import run_task


def test_run_task():
    output = run_task("统计 1 到 100 的和")
    assert "5050" in str(output)