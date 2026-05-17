"""Тесты для FSM состояний бота."""
from aiogram.fsm.state import State

from src.bot.states import PredictionStates


class TestPredictionStates:
    """Тесты для FSM состояний предсказания."""

    def test_prediction_states_exists(self):
        """Тест существования PredictionStates."""
        assert PredictionStates is not None

    def test_waiting_for_zone_state(self):
        """Тест состояния waiting_for_zone."""
        assert hasattr(PredictionStates, 'waiting_for_zone')
        state = PredictionStates.waiting_for_zone
        assert isinstance(state, State)

    def test_waiting_for_crop_state(self):
        """Тест состояния waiting_for_crop."""
        assert hasattr(PredictionStates, 'waiting_for_crop')
        state = PredictionStates.waiting_for_crop
        assert isinstance(state, State)

    def test_waiting_for_date_state(self):
        """Тест состояния waiting_for_date."""
        assert hasattr(PredictionStates, 'waiting_for_date')
        state = PredictionStates.waiting_for_date
        assert isinstance(state, State)

    def test_all_states_in_states_group(self):
        """Тест что все состояния в группе состояний."""
        states = [
            PredictionStates.waiting_for_zone,
            PredictionStates.waiting_for_crop,
            PredictionStates.waiting_for_date,
        ]
        
        for state in states:
            assert state is not None

    def test_state_names(self):
        """Тест корректности имён состояний."""
        # Имена состояний в формате "StateGroup:state"
        assert "waiting_for_zone" in PredictionStates.waiting_for_zone.state
        assert "waiting_for_crop" in PredictionStates.waiting_for_crop.state
        assert "waiting_for_date" in PredictionStates.waiting_for_date.state
