from typing import List, Tuple, Union

import pandas as pd
import xgboost as xgb


class DelayModel:

    FEATURES_COLS = [
        "OPERA_Latin American Wings",
        "MES_7",
        "MES_10",
        "OPERA_Grupo LATAM",
        "MES_12",
        "TIPOVUELO_I",
        "MES_4",
        "MES_11",
        "OPERA_Sky Airline",
        "OPERA_Copa Air",
    ]
    TARGET_COL = "delay"
    DELAY_THRESHOLD_MIN = 15
    DATETIME_FMT = "%Y-%m-%d %H:%M:%S"

    def __init__(
        self
    ):
        self._model = None

    def preprocess(
        self,
        data: pd.DataFrame,
        target_column: str = None
    ) -> Union[Tuple[pd.DataFrame, pd.DataFrame], pd.DataFrame]:
        """
        Prepare raw data for training or predict.

        Args:
            data (pd.DataFrame): raw data.
            target_column (str, optional): if set, the target is returned.

        Returns:
            Tuple[pd.DataFrame, pd.DataFrame]: features and target.
            or
            pd.DataFrame: features.
        """
        features = pd.concat(
            [
                pd.get_dummies(data["OPERA"], prefix="OPERA"),
                pd.get_dummies(data["TIPOVUELO"], prefix="TIPOVUELO"),
                pd.get_dummies(data["MES"], prefix="MES"),
            ],
            axis=1,
        )
        features = features.reindex(columns=self.FEATURES_COLS, fill_value=0)

        if target_column is None:
            return features

        if target_column == self.TARGET_COL and self.TARGET_COL not in data.columns:
            data_o = pd.to_datetime(data["Fecha-O"], format=self.DATETIME_FMT)
            data_i = pd.to_datetime(data["Fecha-I"], format=self.DATETIME_FMT)
            min_diff = (data_o - data_i).dt.total_seconds() / 60
            target = (min_diff > self.DELAY_THRESHOLD_MIN).astype(int)
        else:
            target = data[target_column]

        return features, target.to_frame(name=target_column)

    def fit(
        self,
        features: pd.DataFrame,
        target: pd.DataFrame
    ) -> None:
        """
        Fit model with preprocessed data.

        Args:
            features (pd.DataFrame): preprocessed data.
            target (pd.DataFrame): target.
        """
        target_series = target.iloc[:, 0] if isinstance(target, pd.DataFrame) else target
        n_neg = int((target_series == 0).sum())
        n_pos = int((target_series == 1).sum())
        scale_pos_weight = n_neg / n_pos if n_pos > 0 else 1.0

        self._model = xgb.XGBClassifier(
            random_state=1,
            learning_rate=0.01,
            scale_pos_weight=scale_pos_weight,
        )
        self._model.fit(features, target_series)

    def predict(
        self,
        features: pd.DataFrame
    ) -> List[int]:
        """
        Predict delays for new flights.

        Args:
            features (pd.DataFrame): preprocessed data.

        Returns:
            (List[int]): predicted targets.
        """
        if self._model is None:
            raise RuntimeError("DelayModel.predict called before fit; call fit first.")

        y_pred = self._model.predict(features)
        return [int(p) for p in y_pred]
