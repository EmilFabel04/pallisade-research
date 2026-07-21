from __future__ import annotations

from sqlalchemy import inspect


def test_evaluation_results_table_exists(db):
    insp = inspect(db.bind)
    cols = {c["name"] for c in insp.get_columns("evaluation_results")}
    expected = {
        "id", "run_id", "recommendation", "confidence",
        "final_thesis_md", "key_risks_md", "financial_summary_md",
        "agent_outputs", "tokens_in", "tokens_out", "cost_usd", "created_at",
    }
    assert expected.issubset(cols)


def test_evaluation_results_has_unique_run_id(db):
    insp = inspect(db.bind)
    uniques = insp.get_unique_constraints("evaluation_results")
    indexes = insp.get_indexes("evaluation_results")
    has_unique = any(
        u["column_names"] == ["run_id"] for u in uniques
    ) or any(
        idx["column_names"] == ["run_id"] and idx.get("unique") for idx in indexes
    )
    assert has_unique


def test_evaluation_results_accepts_valid_recommendation(db, make_user):
    """A valid recommendation value passes the CHECK constraint."""
    from sqlalchemy import text
    from pallisade_core.deals.models import Deal
    from pallisade_core.runs.models import EvaluationRun

    u = make_user()
    deal = Deal(name="X", target_company="Y", deal_type="lbo",
                deal_lead_id=u.id, status="screening")
    db.add(deal); db.flush()
    run = EvaluationRun(mode="private", user_id=u.id, deal_id=deal.id,
                         ticker=None, status="done")
    db.add(run); db.flush()

    db.execute(text("""
        INSERT INTO evaluation_results
          (run_id, recommendation, confidence,
           final_thesis_md, key_risks_md, financial_summary_md,
           agent_outputs)
        VALUES (:run_id, 'approve', 0.7, 't', 'r', 'f', '[]'::jsonb)
    """), {"run_id": str(run.id)})
    db.commit()


def test_evaluation_results_rejects_invalid_recommendation(db, make_user):
    """An invalid recommendation value violates the CHECK constraint."""
    import pytest
    from sqlalchemy import text
    from sqlalchemy.exc import IntegrityError
    from pallisade_core.deals.models import Deal
    from pallisade_core.runs.models import EvaluationRun

    u = make_user()
    deal = Deal(name="X", target_company="Y", deal_type="lbo",
                deal_lead_id=u.id, status="screening")
    db.add(deal); db.flush()
    run = EvaluationRun(mode="private", user_id=u.id, deal_id=deal.id,
                         ticker=None, status="done")
    db.add(run); db.flush()

    with pytest.raises(IntegrityError):
        db.execute(text("""
            INSERT INTO evaluation_results
              (run_id, recommendation, confidence,
               final_thesis_md, key_risks_md, financial_summary_md,
               agent_outputs)
            VALUES (:run_id, 'buy', 0.5, 't', 'r', 'f', '[]'::jsonb)
        """), {"run_id": str(run.id)})
        db.commit()
    db.rollback()


def test_evaluation_results_rejects_out_of_range_confidence(db, make_user):
    """Confidence > 1 violates the CHECK constraint."""
    import pytest
    from sqlalchemy import text
    from sqlalchemy.exc import IntegrityError
    from pallisade_core.deals.models import Deal
    from pallisade_core.runs.models import EvaluationRun

    u = make_user()
    deal = Deal(name="X", target_company="Y", deal_type="lbo",
                deal_lead_id=u.id, status="screening")
    db.add(deal); db.flush()
    run = EvaluationRun(mode="private", user_id=u.id, deal_id=deal.id,
                         ticker=None, status="done")
    db.add(run); db.flush()

    with pytest.raises(IntegrityError):
        db.execute(text("""
            INSERT INTO evaluation_results
              (run_id, recommendation, confidence,
               final_thesis_md, key_risks_md, financial_summary_md,
               agent_outputs)
            VALUES (:run_id, 'approve', 1.5, 't', 'r', 'f', '[]'::jsonb)
        """), {"run_id": str(run.id)})
        db.commit()
    db.rollback()
