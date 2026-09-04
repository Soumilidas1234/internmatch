"""Local neural match scores using a scikit-learn multi-layer perceptron."""

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neural_network import MLPClassifier, MLPRegressor


def _pair_features(left, right):
    return np.concatenate([left, right, np.abs(left - right), left * right])


def _domain_label(text):
    lowered = (text or "").lower()
    if lowered.startswith("domain:"):
        return lowered.split(".", 1)[0].replace("domain:", "").strip()
    for domain in (
        "data analytics",
        "data science",
        "machine learning",
        "python development",
        "web development",
        "ui/ux",
        "cybersecurity",
        "cloud",
        "testing",
        "java",
    ):
        if domain in lowered:
            return domain
    return "general"


def compute_neural_scores(student_text, internship_texts):
    """Train a small MLP on internship pairs, then score the student profile.

    This is a local neural network (not ChatGPT). It stays in scikit-learn.
    """
    intern_list = list(internship_texts)
    if len(intern_list) < 2:
        return [0] * len(intern_list)

    documents = [text if str(text).strip() else "internship" for text in intern_list]
    profile = (student_text or "").strip() or "student"

    vectorizer = TfidfVectorizer(stop_words="english", min_df=1, max_features=64)
    try:
        intern_matrix = vectorizer.fit_transform(documents).toarray()
        student_vector = vectorizer.transform([profile]).toarray()[0]
    except ValueError:
        return [0] * len(intern_list)

    labels = [_domain_label(text) for text in documents]
    unique_labels = {label for label in labels}
    features = []
    targets = []
    for i, left in enumerate(intern_matrix):
        for j, right in enumerate(intern_matrix):
            features.append(_pair_features(left, right))
            targets.append(1 if labels[i] == labels[j] else 0)

    feature_array = np.asarray(features, dtype=float)
    if unique_labels == {"general"} or len(unique_labels) < 2:
        model = MLPRegressor(
            hidden_layer_sizes=(32, 16),
            max_iter=500,
            random_state=42,
            solver="adam",
        )
        model.fit(feature_array, np.asarray(targets, dtype=float))
        raw_scores = [
            float(model.predict([_pair_features(student_vector, row)])[0])
            for row in intern_matrix
        ]
    else:
        model = MLPClassifier(
            hidden_layer_sizes=(32, 16),
            max_iter=500,
            random_state=42,
            solver="adam",
        )
        model.fit(feature_array, np.asarray(targets))
        raw_scores = []
        for row in intern_matrix:
            pair = _pair_features(student_vector, row).reshape(1, -1)
            if hasattr(model, "predict_proba"):
                classes = list(model.classes_)
                proba = model.predict_proba(pair)[0]
                raw_scores.append(float(proba[classes.index(1)]) if 1 in classes else 0.0)
            else:
                raw_scores.append(float(model.predict(pair)[0]))

    return [int(round(max(0.0, min(1.0, score)) * 100)) for score in raw_scores]
