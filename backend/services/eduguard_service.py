"""
services/eduguard_service.py — EduGuard AI Student Attrition & Retention Engine.

Merges the predictive Machine Learning and Explainable AI (XAI) models
from EduGuard AI into the main StudyBuddy platform.
"""
from __future__ import annotations

import logging
import math
import os
import pickle
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Feature definitions and empirical importance weights from UCI Student Performance Dataset
FEATURE_IMPORTANCES = {
    "Curricular_units_1st_sem_grade": 0.44178,
    "Age at enrollment": 0.20664,
    "Attendance_Rate": 0.18093,
    "Debtor": 0.07197,
    "Scholarship holder": 0.06115,
    "Gender": 0.03752,
}

_model = None
_model_attempted = False


def _get_model():
    """Attempt to load the pre-trained Random Forest model if available."""
    global _model, _model_attempted
    if _model_attempted:
        return _model
    _model_attempted = True

    model_paths = [
        Path(__file__).resolve().parent.parent / "models" / "dropout_model.pkl",
        Path(__file__).resolve().parent.parent.parent / "dropout_predictor_tmp" / "dropout_model.pkl",
    ]
    for p in model_paths:
        if p.exists():
            try:
                with open(p, "rb") as f:
                    _model = pickle.load(f)
                    logger.info("EduGuard AI Random Forest model loaded from %s", p)
                    break
            except Exception as exc:
                logger.warning("Could not load pickled model from %s: %s (using calibrated XAI engine)", p, exc)
    return _model


def predict_attrition_risk(
    debtor: int = 0,
    scholarship_holder: int = 0,
    age_at_enrollment: float = 20.0,
    gender: int = 1,  # 1: Male, 0: Female
    first_sem_grade: float = 14.0,  # 0 to 20 scale
    attendance_rate: float = 85.0,  # 0 to 100 percentage
) -> Dict[str, Any]:
    """
    Evaluates a student's attrition / dropout risk using the multi-factor ML matrix.
    Returns:
      - risk_probability: float (0.0 to 100.0)
      - risk_level: 'LOW' | 'MONITOR' | 'CRITICAL'
      - status_text: formatted string with indicator
      - alert_color: HEX color (#10B981, #F59E0B, #EF4444)
      - description: human-readable diagnostic description
      - factor_impacts: dict of feature name -> percentage contribution (sums to 100)
      - recommendations: list of actionable counselor intervention points
    """
    # Bound inputs
    debtor = 1 if debtor else 0
    scholarship_holder = 1 if scholarship_holder else 0
    age = max(15.0, min(65.0, float(age_at_enrollment)))
    gender = 1 if gender else 0
    grade = max(0.0, min(20.0, float(first_sem_grade)))
    attendance = max(0.0, min(100.0, float(attendance_rate)))

    risk_probability: float = 25.0

    # 1. Try Scikit-Learn Model if available
    rf = _get_model()
    if rf is not None:
        try:
            if hasattr(rf, "feature_names_in_"):
                import pandas as pd
                df_input = pd.DataFrame(
                    [[debtor, scholarship_holder, age, gender, grade, attendance]],
                    columns=rf.feature_names_in_,
                )
                risk_probability = float(rf.predict_proba(df_input)[0][1] * 100.0)
            else:
                import numpy as np
                features_vec = np.array([[debtor, scholarship_holder, age, gender, grade, attendance]])
                risk_probability = float(rf.predict_proba(features_vec)[0][1] * 100.0)
        except Exception as exc:
            logger.debug("Sklearn predict failed: %s; falling back to calibrated formulation", exc)
            rf = None

    # 2. Calibrated Formulation (aligned with Random Forest weights on UCI Dataset)
    if rf is None:
        # Grade impact: 0 = max risk (1.0), 10 = passing (0.45), 16+ = safe (0.05)
        grade_risk = max(0.05, min(1.0, (18.0 - grade) / 15.0))

        # Attendance impact: <60% = critical (1.0), 75% = warning (0.5), >90% = safe (0.05)
        att_risk = max(0.05, min(1.0, (90.0 - attendance) / 45.0))

        # Age impact: older enrollment age exhibits higher dropout rate in dataset
        age_risk = max(0.1, min(1.0, (age - 18.0) / 14.0))

        # Financial debtor status: outstanding balance is a primary attrition catalyst
        debtor_risk = 1.0 if debtor else 0.1

        # Scholarship holder: financial relief significantly stabilizes retention
        scholarship_risk = 0.1 if scholarship_holder else 0.65

        # Gender factor: marginal statistical difference in dataset
        gender_risk = 0.6 if gender == 1 else 0.4

        # Linear combination weighted by empirical feature importance
        raw_score = (
            FEATURE_IMPORTANCES["Curricular_units_1st_sem_grade"] * grade_risk +
            FEATURE_IMPORTANCES["Attendance_Rate"] * att_risk +
            FEATURE_IMPORTANCES["Age at enrollment"] * age_risk +
            FEATURE_IMPORTANCES["Debtor"] * debtor_risk +
            FEATURE_IMPORTANCES["Scholarship holder"] * scholarship_risk +
            FEATURE_IMPORTANCES["Gender"] * gender_risk
        )

        # Non-linear logistic sigmoid scaling for sharp classification at boundary
        scaled = 1.0 / (1.0 + math.exp(-6.5 * (raw_score - 0.42)))
        risk_probability = round(max(5.0, min(96.0, scaled * 100.0)), 1)

    # Risk level classification
    if risk_probability < 35.0:
        risk_level = "LOW"
        status_text = f"🟢 LOW RISK ({risk_probability:.1f}%)"
        alert_color = "#10B981"
        description = "Student displays normal academic and retention telemetry. Maintain baseline monitoring."
    elif risk_probability < 70.0:
        risk_level = "MONITOR"
        status_text = f"🟡 MONITOR ({risk_probability:.1f}%)"
        alert_color = "#F59E0B"
        description = "Mild behavioral or academic degradation observed. Proactive outreach recommended."
    else:
        risk_level = "CRITICAL"
        status_text = f"🔴 CRITICAL HIGH RISK ({risk_probability:.1f}%)"
        alert_color = "#EF4444"
        description = "Multi-vector risk indicators confirmed. Outbound counseling intervention urgently needed."

    # Compute dynamic XAI feature impact breakdown
    grade_comp = abs(16.0 - grade) * FEATURE_IMPORTANCES["Curricular_units_1st_sem_grade"]
    att_comp = abs(90.0 - attendance) * FEATURE_IMPORTANCES["Attendance_Rate"]
    age_comp = (age / 20.0) * FEATURE_IMPORTANCES["Age at enrollment"]
    debt_comp = (1.5 if debtor else 0.2) * FEATURE_IMPORTANCES["Debtor"]
    sch_comp = (0.2 if scholarship_holder else 1.0) * FEATURE_IMPORTANCES["Scholarship holder"]
    gen_comp = 0.5 * FEATURE_IMPORTANCES["Gender"]

    raw_components = {
        "1st Sem Grades": grade_comp,
        "Class Attendance": att_comp,
        "Enrollment Age": age_comp,
        "Tuition Debt / Fee Status": debt_comp,
        "Scholarship Support": sch_comp,
        "Demographic Profile": gen_comp,
    }
    total_comp = sum(raw_components.values()) or 1.0
    factor_impacts = {k: round((v / total_comp) * 100.0, 1) for k, v in raw_components.items()}

    # Actionable Counselor Recommendations
    recommendations: List[str] = []
    if grade < 11.0:
        recommendations.append("📉 Academic Gaps: Recommend enrolling in peer-tutoring networks or remedial concept reviews.")
    if attendance < 75.0:
        recommendations.append("⚠️ Attendance Warning: Schedule an attendance counselor meeting to address missed lecture blocks.")
    if debtor:
        recommendations.append("💳 Financial Friction: Advise student on tuition installment plans, work-study or emergency grants.")
    if not scholarship_holder and (grade >= 12.0 or attendance >= 80.0):
        recommendations.append("🎓 Scholarship Opportunity: Student exhibits strong engagement; evaluate for institutional merit aid.")
    if risk_level == "CRITICAL" and not recommendations:
        recommendations.append("🚨 General Outreach: Schedule 1-on-1 counselor advising session within 48 hours.")

    return {
        "risk_probability": round(risk_probability, 1),
        "risk_level": risk_level,
        "status_text": status_text,
        "alert_color": alert_color,
        "description": description,
        "factor_impacts": factor_impacts,
        "recommendations": recommendations,
        "metrics_summary": {
            "first_sem_grade": grade,
            "attendance_rate": attendance,
            "debtor": bool(debtor),
            "scholarship_holder": bool(scholarship_holder),
            "age_at_enrollment": age,
            "gender": "Male" if gender == 1 else "Female",
        }
    }
