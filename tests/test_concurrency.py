from concurrent.futures import ThreadPoolExecutor
from gaia.api.dependencies import db_session
from gaia.domain import LOCK


def test_db_dependency_can_close_in_a_different_worker_thread():
    """FastAPI's sync dependency entry/exit are not guaranteed the same worker."""
    dependency = db_session()
    next(dependency)
    with ThreadPoolExecutor(max_workers=1) as pool:
        pool.submit(dependency.close).result(timeout=5)
    assert LOCK.acquire(blocking=False), "Request exit must release the shared lock"
    LOCK.release()
