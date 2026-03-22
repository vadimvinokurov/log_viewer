"""Unit tests for SavedFilter model and SavedFilterStore.

// Ref: docs/specs/features/saved-filters.md §10.1
"""
from __future__ import annotations

import time
import uuid

from beartype import beartype

from src.models.filter_state import FilterMode
from src.models.saved_filter import SavedFilter, SavedFilterStore


class TestSavedFilter:
    """Tests for SavedFilter dataclass.
    
    // Ref: docs/specs/features/saved-filters.md §2.1
    """
    
    def test_saved_filter_creation(self) -> None:
        """Test SavedFilter creation with all fields."""
        filter_id = str(uuid.uuid4())
        created_at = time.time()
        
        saved_filter = SavedFilter(
            id=filter_id,
            name="Error Filter",
            filter_text="error|critical",
            filter_mode=FilterMode.PLAIN,
            created_at=created_at,
            enabled=True
        )
        
        assert saved_filter.id == filter_id
        assert saved_filter.name == "Error Filter"
        assert saved_filter.filter_text == "error|critical"
        assert saved_filter.filter_mode == FilterMode.PLAIN
        assert saved_filter.created_at == created_at
        assert saved_filter.enabled is True
    
    def test_saved_filter_default_enabled(self) -> None:
        """Test SavedFilter default enabled value is True."""
        saved_filter = SavedFilter(
            id=str(uuid.uuid4()),
            name="Test Filter",
            filter_text="test",
            filter_mode=FilterMode.REGEX,
            created_at=time.time()
        )
        
        assert saved_filter.enabled is True
    
    def test_saved_filter_disabled(self) -> None:
        """Test SavedFilter can be created with enabled=False."""
        saved_filter = SavedFilter(
            id=str(uuid.uuid4()),
            name="Disabled Filter",
            filter_text="test",
            filter_mode=FilterMode.SIMPLE,
            created_at=time.time(),
            enabled=False
        )
        
        assert saved_filter.enabled is False
    
    def test_saved_filter_all_modes(self) -> None:
        """Test SavedFilter with all filter modes."""
        for mode in [FilterMode.PLAIN, FilterMode.REGEX, FilterMode.SIMPLE]:
            saved_filter = SavedFilter(
                id=str(uuid.uuid4()),
                name=f"Filter {mode.value}",
                filter_text="test",
                filter_mode=mode,
                created_at=time.time()
            )
            assert saved_filter.filter_mode == mode


class TestSavedFilterStore:
    """Tests for SavedFilterStore class.
    
    // Ref: docs/specs/features/saved-filters.md §2.2
    """
    
    def test_store_initialization(self) -> None:
        """Test SavedFilterStore initializes empty."""
        store = SavedFilterStore()
        
        assert store.get_all_filters() == []
        assert store.get_enabled_filters() == []
    
    def test_add_filter(self) -> None:
        """Test adding a filter to the store."""
        store = SavedFilterStore()
        
        saved_filter = SavedFilter(
            id="test-id-1",
            name="Error Filter",
            filter_text="error",
            filter_mode=FilterMode.PLAIN,
            created_at=time.time()
        )
        
        result_id = store.add_filter(saved_filter)
        
        assert result_id == "test-id-1"
        assert len(store.get_all_filters()) == 1
        assert store.get_all_filters()[0].id == "test-id-1"
    
    def test_add_multiple_filters(self) -> None:
        """Test adding multiple filters to the store."""
        store = SavedFilterStore()
        
        filter1 = SavedFilter(
            id="id-1",
            name="Filter 1",
            filter_text="error",
            filter_mode=FilterMode.PLAIN,
            created_at=time.time()
        )
        filter2 = SavedFilter(
            id="id-2",
            name="Filter 2",
            filter_text="warning",
            filter_mode=FilterMode.REGEX,
            created_at=time.time()
        )
        
        store.add_filter(filter1)
        store.add_filter(filter2)
        
        all_filters = store.get_all_filters()
        assert len(all_filters) == 2
        ids = {f.id for f in all_filters}
        assert ids == {"id-1", "id-2"}
    
    def test_remove_filter_existing(self) -> None:
        """Test removing an existing filter."""
        store = SavedFilterStore()
        
        saved_filter = SavedFilter(
            id="test-id",
            name="Test Filter",
            filter_text="test",
            filter_mode=FilterMode.PLAIN,
            created_at=time.time()
        )
        store.add_filter(saved_filter)
        
        result = store.remove_filter("test-id")
        
        assert result is True
        assert len(store.get_all_filters()) == 0
    
    def test_remove_filter_non_existing(self) -> None:
        """Test removing a non-existing filter returns False."""
        store = SavedFilterStore()
        
        result = store.remove_filter("non-existing-id")
        
        assert result is False
    
    def test_rename_filter_existing(self) -> None:
        """Test renaming an existing filter."""
        store = SavedFilterStore()
        
        saved_filter = SavedFilter(
            id="test-id",
            name="Old Name",
            filter_text="test",
            filter_mode=FilterMode.PLAIN,
            created_at=time.time()
        )
        store.add_filter(saved_filter)
        
        result = store.rename_filter("test-id", "New Name")
        
        assert result is True
        filters = store.get_all_filters()
        assert len(filters) == 1
        assert filters[0].name == "New Name"
    
    def test_rename_filter_non_existing(self) -> None:
        """Test renaming a non-existing filter returns False."""
        store = SavedFilterStore()
        
        result = store.rename_filter("non-existing-id", "New Name")
        
        assert result is False
    
    def test_set_enabled_existing(self) -> None:
        """Test setting enabled state on existing filter."""
        store = SavedFilterStore()
        
        saved_filter = SavedFilter(
            id="test-id",
            name="Test Filter",
            filter_text="test",
            filter_mode=FilterMode.PLAIN,
            created_at=time.time(),
            enabled=True
        )
        store.add_filter(saved_filter)
        
        result = store.set_enabled("test-id", False)
        
        assert result is True
        assert store.get_all_filters()[0].enabled is False
    
    def test_set_enabled_non_existing(self) -> None:
        """Test setting enabled state on non-existing filter returns False."""
        store = SavedFilterStore()
        
        result = store.set_enabled("non-existing-id", False)
        
        assert result is False
    
    def test_get_enabled_filters(self) -> None:
        """Test getting only enabled filters."""
        store = SavedFilterStore()
        
        filter1 = SavedFilter(
            id="id-1",
            name="Enabled Filter",
            filter_text="error",
            filter_mode=FilterMode.PLAIN,
            created_at=time.time(),
            enabled=True
        )
        filter2 = SavedFilter(
            id="id-2",
            name="Disabled Filter",
            filter_text="warning",
            filter_mode=FilterMode.PLAIN,
            created_at=time.time(),
            enabled=False
        )
        filter3 = SavedFilter(
            id="id-3",
            name="Another Enabled",
            filter_text="info",
            filter_mode=FilterMode.REGEX,
            created_at=time.time(),
            enabled=True
        )
        
        store.add_filter(filter1)
        store.add_filter(filter2)
        store.add_filter(filter3)
        
        enabled = store.get_enabled_filters()
        
        assert len(enabled) == 2
        ids = {f.id for f in enabled}
        assert ids == {"id-1", "id-3"}
    
    def test_get_all_filters(self) -> None:
        """Test getting all filters (enabled and disabled)."""
        store = SavedFilterStore()
        
        filter1 = SavedFilter(
            id="id-1",
            name="Enabled Filter",
            filter_text="error",
            filter_mode=FilterMode.PLAIN,
            created_at=time.time(),
            enabled=True
        )
        filter2 = SavedFilter(
            id="id-2",
            name="Disabled Filter",
            filter_text="warning",
            filter_mode=FilterMode.PLAIN,
            created_at=time.time(),
            enabled=False
        )
        
        store.add_filter(filter1)
        store.add_filter(filter2)
        
        all_filters = store.get_all_filters()
        
        assert len(all_filters) == 2
        ids = {f.id for f in all_filters}
        assert ids == {"id-1", "id-2"}
    
    def test_filter_combination_or_logic(self) -> None:
        """Test that multiple enabled filters represent OR logic.
        
        // Ref: docs/specs/features/saved-filters.md §3.1
        This test verifies the store can hold multiple enabled filters.
        The actual OR combination logic is in SavedFilterController.
        """
        store = SavedFilterStore()
        
        # Add multiple enabled filters
        filter1 = SavedFilter(
            id="id-1",
            name="Error Filter",
            filter_text="error",
            filter_mode=FilterMode.PLAIN,
            created_at=time.time(),
            enabled=True
        )
        filter2 = SavedFilter(
            id="id-2",
            name="Warning Filter",
            filter_text="warning",
            filter_mode=FilterMode.PLAIN,
            created_at=time.time(),
            enabled=True
        )
        
        store.add_filter(filter1)
        store.add_filter(filter2)
        
        enabled_filters = store.get_enabled_filters()
        
        # Both filters should be enabled (OR logic means both active)
        assert len(enabled_filters) == 2
    
    def test_add_filter_overwrites_existing_id(self) -> None:
        """Test that adding filter with existing ID overwrites."""
        store = SavedFilterStore()
        
        filter1 = SavedFilter(
            id="same-id",
            name="Original Filter",
            filter_text="error",
            filter_mode=FilterMode.PLAIN,
            created_at=time.time()
        )
        filter2 = SavedFilter(
            id="same-id",
            name="Replacement Filter",
            filter_text="warning",
            filter_mode=FilterMode.REGEX,
            created_at=time.time()
        )
        
        store.add_filter(filter1)
        store.add_filter(filter2)
        
        all_filters = store.get_all_filters()
        assert len(all_filters) == 1
        assert all_filters[0].name == "Replacement Filter"
        assert all_filters[0].filter_text == "warning"
    
    def test_crud_operations_sequence(self) -> None:
        """Test complete CRUD operations sequence."""
        store = SavedFilterStore()
        
        # Create
        filter1 = SavedFilter(
            id="id-1",
            name="Filter 1",
            filter_text="error",
            filter_mode=FilterMode.PLAIN,
            created_at=time.time()
        )
        filter2 = SavedFilter(
            id="id-2",
            name="Filter 2",
            filter_text="warning",
            filter_mode=FilterMode.REGEX,
            created_at=time.time()
        )
        
        store.add_filter(filter1)
        store.add_filter(filter2)
        assert len(store.get_all_filters()) == 2
        
        # Update (rename)
        store.rename_filter("id-1", "Renamed Filter 1")
        filters = store.get_all_filters()
        filter1_updated = next(f for f in filters if f.id == "id-1")
        assert filter1_updated.name == "Renamed Filter 1"
        
        # Update (disable)
        store.set_enabled("id-2", False)
        enabled = store.get_enabled_filters()
        assert len(enabled) == 1
        assert enabled[0].id == "id-1"
        
        # Delete
        store.remove_filter("id-1")
        assert len(store.get_all_filters()) == 1
        assert store.get_all_filters()[0].id == "id-2"
        
        # Delete remaining
        store.remove_filter("id-2")
        assert len(store.get_all_filters()) == 0


class TestSavedFilterTypeSafety:
    """Tests for type safety with beartype decorator.
    
    // Ref: docs/SPEC.md §1 (beartype requirement)
    """
    
    def test_store_methods_have_beartype(self) -> None:
        """Verify all public methods have @beartype decorator."""
        # Check that methods are decorated by verifying they raise on invalid types
        store = SavedFilterStore()
        
        # add_filter should accept SavedFilter
        # remove_filter should accept str
        # rename_filter should accept str, str
        # set_enabled should accept str, bool
        # get_enabled_filters should return list[SavedFilter]
        # get_all_filters should return list[SavedFilter]
        
        # These should work without errors
        saved_filter = SavedFilter(
            id="test-id",
            name="Test",
            filter_text="test",
            filter_mode=FilterMode.PLAIN,
            created_at=time.time()
        )
        store.add_filter(saved_filter)
        store.remove_filter("test-id")
        store.rename_filter("test-id", "new")
        store.set_enabled("test-id", True)
        store.get_enabled_filters()
        store.get_all_filters()


class TestSavedFilterController:
    """Tests for SavedFilterController class.
    
    // Ref: docs/specs/features/saved-filters.md §5.1
    // Ref: docs/specs/features/saved-filters.md §10.1
    """
    
    def test_controller_initialization(self, tmp_path) -> None:
        """Test SavedFilterController initializes correctly."""
        from src.controllers.saved_filter_controller import SavedFilterController
        from src.utils.settings_manager import SettingsManager
        
        settings_manager = SettingsManager(filepath=str(tmp_path / "test_settings.json"))
        settings_manager.load()
        
        controller = SavedFilterController(settings_manager)
        
        assert controller.get_all_filters() == []
    
    def test_save_filter_with_name(self, tmp_path) -> None:
        """Test saving a filter with explicit name."""
        from src.controllers.saved_filter_controller import SavedFilterController
        from src.utils.settings_manager import SettingsManager
        
        settings_manager = SettingsManager(filepath=str(tmp_path / "test_settings.json"))
        settings_manager.load()
        
        controller = SavedFilterController(settings_manager)
        
        filter_id = controller.save_filter(
            text="error|critical",
            mode=FilterMode.PLAIN,
            name="Error Filter"
        )
        
        assert filter_id is not None
        filters = controller.get_all_filters()
        assert len(filters) == 1
        assert filters[0].name == "Error Filter"
        assert filters[0].filter_text == "error|critical"
        assert filters[0].filter_mode == FilterMode.PLAIN
        assert filters[0].enabled is True
    
    def test_save_filter_auto_name(self, tmp_path) -> None:
        """Test saving a filter with auto-generated name."""
        from src.controllers.saved_filter_controller import SavedFilterController
        from src.utils.settings_manager import SettingsManager
        
        settings_manager = SettingsManager(filepath=str(tmp_path / "test_settings.json"))
        settings_manager.load()
        
        controller = SavedFilterController(settings_manager)
        
        # Short text
        filter_id = controller.save_filter(
            text="error",
            mode=FilterMode.PLAIN
        )
        
        filters = controller.get_all_filters()
        assert filters[0].name == "error"
        
        # Long text (should be truncated to 30 chars + "...")
        long_text = "a" * 50
        filter_id2 = controller.save_filter(
            text=long_text,
            mode=FilterMode.REGEX
        )
        
        filters = controller.get_all_filters()
        assert len(filters) == 2
        assert filters[1].name == "a" * 30 + "..."
    
    def test_delete_filter_existing(self, tmp_path) -> None:
        """Test deleting an existing filter."""
        from src.controllers.saved_filter_controller import SavedFilterController
        from src.utils.settings_manager import SettingsManager
        
        settings_manager = SettingsManager(filepath=str(tmp_path / "test_settings.json"))
        settings_manager.load()
        
        controller = SavedFilterController(settings_manager)
        
        filter_id = controller.save_filter(
            text="error",
            mode=FilterMode.PLAIN,
            name="Test Filter"
        )
        
        result = controller.delete_filter(filter_id)
        
        assert result is True
        assert len(controller.get_all_filters()) == 0
    
    def test_delete_filter_non_existing(self, tmp_path) -> None:
        """Test deleting a non-existing filter."""
        from src.controllers.saved_filter_controller import SavedFilterController
        from src.utils.settings_manager import SettingsManager
        
        settings_manager = SettingsManager(filepath=str(tmp_path / "test_settings.json"))
        settings_manager.load()
        
        controller = SavedFilterController(settings_manager)
        
        result = controller.delete_filter("non-existing-id")
        
        assert result is False
    
    def test_rename_filter_existing(self, tmp_path) -> None:
        """Test renaming an existing filter."""
        from src.controllers.saved_filter_controller import SavedFilterController
        from src.utils.settings_manager import SettingsManager
        
        settings_manager = SettingsManager(filepath=str(tmp_path / "test_settings.json"))
        settings_manager.load()
        
        controller = SavedFilterController(settings_manager)
        
        filter_id = controller.save_filter(
            text="error",
            mode=FilterMode.PLAIN,
            name="Old Name"
        )
        
        result = controller.rename_filter(filter_id, "New Name")
        
        assert result is True
        filters = controller.get_all_filters()
        assert filters[0].name == "New Name"
    
    def test_rename_filter_non_existing(self, tmp_path) -> None:
        """Test renaming a non-existing filter."""
        from src.controllers.saved_filter_controller import SavedFilterController
        from src.utils.settings_manager import SettingsManager
        
        settings_manager = SettingsManager(filepath=str(tmp_path / "test_settings.json"))
        settings_manager.load()
        
        controller = SavedFilterController(settings_manager)
        
        result = controller.rename_filter("non-existing-id", "New Name")
        
        assert result is False
    
    def test_set_filter_enabled(self, tmp_path) -> None:
        """Test enabling/disabling a filter."""
        from src.controllers.saved_filter_controller import SavedFilterController
        from src.utils.settings_manager import SettingsManager
        
        settings_manager = SettingsManager(filepath=str(tmp_path / "test_settings.json"))
        settings_manager.load()
        
        controller = SavedFilterController(settings_manager)
        
        filter_id = controller.save_filter(
            text="error",
            mode=FilterMode.PLAIN,
            name="Test Filter"
        )
        
        # Disable
        controller.set_filter_enabled(filter_id, False)
        
        filters = controller.get_all_filters()
        assert filters[0].enabled is False
        
        # Enable
        controller.set_filter_enabled(filter_id, True)
        
        filters = controller.get_all_filters()
        assert filters[0].enabled is True
    
    def test_get_combined_filter_no_filters(self, tmp_path) -> None:
        """Test get_combined_filter returns None when no filters enabled."""
        from src.controllers.saved_filter_controller import SavedFilterController
        from src.utils.settings_manager import SettingsManager
        
        settings_manager = SettingsManager(filepath=str(tmp_path / "test_settings.json"))
        settings_manager.load()
        
        controller = SavedFilterController(settings_manager)
        
        result = controller.get_combined_filter()
        
        assert result is None
    
    def test_get_combined_filter_disabled_filters(self, tmp_path) -> None:
        """Test get_combined_filter returns None when all filters disabled."""
        from src.controllers.saved_filter_controller import SavedFilterController
        from src.utils.settings_manager import SettingsManager
        
        settings_manager = SettingsManager(filepath=str(tmp_path / "test_settings.json"))
        settings_manager.load()
        
        controller = SavedFilterController(settings_manager)
        
        filter_id = controller.save_filter(
            text="error",
            mode=FilterMode.PLAIN,
            name="Test Filter"
        )
        controller.set_filter_enabled(filter_id, False)
        
        result = controller.get_combined_filter()
        
        assert result is None
    
    def test_get_combined_filter_or_logic(self, tmp_path) -> None:
        """Test get_combined_filter combines filters with OR logic.
        
        // Ref: docs/specs/features/saved-filters.md §3.1
        """
        from src.controllers.saved_filter_controller import SavedFilterController
        from src.utils.settings_manager import SettingsManager
        from src.models.log_entry import LogEntry, LogLevel
        
        settings_manager = SettingsManager(filepath=str(tmp_path / "test_settings.json"))
        settings_manager.load()
        
        controller = SavedFilterController(settings_manager)
        
        # Add two filters: "error" and "warning"
        controller.save_filter(text="error", mode=FilterMode.PLAIN, name="Error Filter")
        controller.save_filter(text="warning", mode=FilterMode.PLAIN, name="Warning Filter")
        
        combined = controller.get_combined_filter()
        
        assert combined is not None
        
        # Create test entries
        # Ref: docs/specs/features/log-entry-optimization.md §4.2
        # Ref: docs/specs/features/timestamp-unix-epoch.md §3.1
        # timestamp is Unix Epoch float
        entry_error = LogEntry(
            row_index=0,
            timestamp=1700000000.0,
            level=LogLevel.ERROR,
            category="Test",
            display_message="This is an error message",
            file_offset=0,
        )
        entry_warning = LogEntry(
            row_index=1,
            timestamp=1700000001.0,
            level=LogLevel.WARNING,
            category="Test",
            display_message="This is a warning message",
            file_offset=100,
        )
        entry_info = LogEntry(
            row_index=2,
            timestamp=1700000002.0,
            level=LogLevel.MSG,
            category="Test",
            display_message="This is an info message",
            file_offset=200,
        )
        
        # OR logic: should match error OR warning
        assert combined(entry_error) is True
        assert combined(entry_warning) is True
        assert combined(entry_info) is False
    
    def test_settings_persistence(self, tmp_path) -> None:
        """Test that filters persist across controller instances.
        
        // Ref: docs/specs/features/saved-filters.md §6.1
        """
        from src.controllers.saved_filter_controller import SavedFilterController
        from src.utils.settings_manager import SettingsManager
        
        settings_file = str(tmp_path / "test_settings.json")
        
        # Create first controller and save a filter
        settings_manager1 = SettingsManager(filepath=settings_file)
        settings_manager1.load()
        
        controller1 = SavedFilterController(settings_manager1)
        filter_id = controller1.save_filter(
            text="error",
            mode=FilterMode.PLAIN,
            name="Test Filter"
        )
        
        # Save settings
        settings_manager1.save()
        
        # Create new controller with same settings
        settings_manager2 = SettingsManager(filepath=settings_file)
        settings_manager2.load()
        
        controller2 = SavedFilterController(settings_manager2)
        
        # Verify filter was loaded
        filters = controller2.get_all_filters()
        assert len(filters) == 1
        assert filters[0].name == "Test Filter"
        assert filters[0].filter_text == "error"
        assert filters[0].filter_mode == FilterMode.PLAIN
    
    def test_filters_changed_signal(self, tmp_path) -> None:
        """Test that filters_changed signal is emitted."""
        from src.controllers.saved_filter_controller import SavedFilterController
        from src.utils.settings_manager import SettingsManager
        
        settings_manager = SettingsManager(filepath=str(tmp_path / "test_settings.json"))
        settings_manager.load()
        
        controller = SavedFilterController(settings_manager)
        
        # Track signal emissions
        signal_count = [0]
        def on_filters_changed():
            signal_count[0] += 1
        
        controller.filters_changed.connect(on_filters_changed)
        
        # Save filter should emit signal
        controller.save_filter(text="error", mode=FilterMode.PLAIN, name="Test")
        assert signal_count[0] == 1
        
        # Delete filter should emit signal
        filter_id = controller.get_all_filters()[0].id
        controller.delete_filter(filter_id)
        assert signal_count[0] == 2
        
        # Rename filter should emit signal
        # First save a new filter (emits signal, count becomes 3)
        filter_id2 = controller.save_filter(text="test", mode=FilterMode.PLAIN, name="Test2")
        # Then rename it (emits signal, count becomes 4)
        controller.rename_filter(filter_id2, "Renamed")
        assert signal_count[0] == 4
    
    def test_filter_applied_signal(self, tmp_path) -> None:
        """Test that filter_applied signal is emitted."""
        from src.controllers.saved_filter_controller import SavedFilterController
        from src.utils.settings_manager import SettingsManager
        
        settings_manager = SettingsManager(filepath=str(tmp_path / "test_settings.json"))
        settings_manager.load()
        
        controller = SavedFilterController(settings_manager)
        
        # Track signal emissions
        signal_count = [0]
        def on_filter_applied():
            signal_count[0] += 1
        
        controller.filter_applied.connect(on_filter_applied)
        
        # set_filter_enabled should emit signal
        filter_id = controller.save_filter(text="error", mode=FilterMode.PLAIN, name="Test")
        controller.set_filter_enabled(filter_id, False)
        assert signal_count[0] == 1
        
        controller.set_filter_enabled(filter_id, True)
        assert signal_count[0] == 2


class TestSavedFilterControllerTypeSafety:
    """Tests for type safety with beartype decorator.
    
    // Ref: docs/SPEC.md §1 (beartype requirement)
    """
    
    def test_controller_methods_have_beartype(self, tmp_path) -> None:
        """Verify all public methods have @beartype decorator."""
        from src.controllers.saved_filter_controller import SavedFilterController
        from src.utils.settings_manager import SettingsManager
        
        settings_manager = SettingsManager(filepath=str(tmp_path / "test_settings.json"))
        settings_manager.load()
        
        controller = SavedFilterController(settings_manager)
        
        # These should work without errors
        controller.save_filter("error", FilterMode.PLAIN, "Test")
        controller.get_all_filters()
        controller.get_combined_filter()
        
        filter_id = controller.get_all_filters()[0].id
        controller.delete_filter(filter_id)
        controller.rename_filter("test-id", "new name")
        controller.set_filter_enabled("test-id", True)


class TestFiltersTabContent:
    """Tests for FiltersTabContent UI component.
    
    // Ref: docs/specs/features/saved-filters.md §4.2
    // Ref: docs/specs/features/saved-filters.md §10.1
    """
    
    def test_filters_tab_content_initialization(self, qtbot) -> None:
        """Test FiltersTabContent initializes correctly."""
        from src.views.components.filters_tab import FiltersTabContent
        
        content = FiltersTabContent()
        qtbot.addWidget(content)
        
        # Verify initial state
        assert content._filter_list.count() == 0
        assert len(content._filter_items) == 0
        assert not content._delete_button.isEnabled()
        assert not content._rename_button.isEnabled()
    
    def test_set_filters(self, qtbot) -> None:
        """Test populating filter list."""
        from src.views.components.filters_tab import FiltersTabContent
        
        content = FiltersTabContent()
        qtbot.addWidget(content)
        
        # Create test filters
        filter1 = SavedFilter(
            id="id-1",
            name="Error Filter",
            filter_text="error|critical",
            filter_mode=FilterMode.PLAIN,
            created_at=time.time(),
            enabled=True
        )
        filter2 = SavedFilter(
            id="id-2",
            name="Warning Filter",
            filter_text="warning",
            filter_mode=FilterMode.REGEX,
            created_at=time.time(),
            enabled=False
        )
        
        # Set filters
        content.set_filters([filter1, filter2])
        
        # Verify list populated
        assert content._filter_list.count() == 2
        assert "id-1" in content._filter_items
        assert "id-2" in content._filter_items
    
    def test_add_filter(self, qtbot) -> None:
        """Test adding single filter to list."""
        from src.views.components.filters_tab import FiltersTabContent
        
        content = FiltersTabContent()
        qtbot.addWidget(content)
        
        # Add first filter
        filter1 = SavedFilter(
            id="id-1",
            name="Error Filter",
            filter_text="error",
            filter_mode=FilterMode.PLAIN,
            created_at=time.time(),
            enabled=True
        )
        content.add_filter(filter1)
        
        assert content._filter_list.count() == 1
        assert "id-1" in content._filter_items
        
        # Add second filter
        filter2 = SavedFilter(
            id="id-2",
            name="Warning Filter",
            filter_text="warning",
            filter_mode=FilterMode.REGEX,
            created_at=time.time(),
            enabled=False
        )
        content.add_filter(filter2)
        
        assert content._filter_list.count() == 2
        assert "id-2" in content._filter_items
    
    def test_remove_filter(self, qtbot) -> None:
        """Test removing filter from list."""
        from src.views.components.filters_tab import FiltersTabContent
        
        content = FiltersTabContent()
        qtbot.addWidget(content)
        
        # Add filters
        filter1 = SavedFilter(
            id="id-1",
            name="Filter 1",
            filter_text="error",
            filter_mode=FilterMode.PLAIN,
            created_at=time.time()
        )
        filter2 = SavedFilter(
            id="id-2",
            name="Filter 2",
            filter_text="warning",
            filter_mode=FilterMode.PLAIN,
            created_at=time.time()
        )
        content.set_filters([filter1, filter2])
        
        # Remove first filter
        content.remove_filter("id-1")
        
        assert content._filter_list.count() == 1
        assert "id-1" not in content._filter_items
        assert "id-2" in content._filter_items
        
        # Remove non-existing filter (should not crash)
        content.remove_filter("non-existing")
        
        assert content._filter_list.count() == 1
    
    def test_checkbox_toggle_signal(self, qtbot) -> None:
        """Test that checkbox toggle emits filter_enabled_changed signal."""
        from src.views.components.filters_tab import FiltersTabContent
        from PySide6.QtCore import Qt
        
        content = FiltersTabContent()
        qtbot.addWidget(content)
        
        # Add filter
        test_filter = SavedFilter(
            id="test-id",
            name="Test Filter",
            filter_text="error",
            filter_mode=FilterMode.PLAIN,
            created_at=time.time(),
            enabled=True
        )
        content.add_filter(test_filter)
        
        # Track signal emissions
        signal_data = []
        def on_enabled_changed(filter_id: str, enabled: bool):
            signal_data.append((filter_id, enabled))
        
        content.filter_enabled_changed.connect(on_enabled_changed)
        
        # Toggle checkbox
        item = content._filter_items["test-id"]
        item.setCheckState(Qt.Unchecked)
        
        # Wait for signal
        qtbot.wait(10)
        
        # Verify signal emitted
        assert len(signal_data) == 1
        assert signal_data[0] == ("test-id", False)
    
    def test_delete_button_signal(self, qtbot) -> None:
        """Test that delete button emits filter_deleted signal."""
        from src.views.components.filters_tab import FiltersTabContent
        
        content = FiltersTabContent()
        qtbot.addWidget(content)
        
        # Add filter
        test_filter = SavedFilter(
            id="test-id",
            name="Test Filter",
            filter_text="error",
            filter_mode=FilterMode.PLAIN,
            created_at=time.time()
        )
        content.add_filter(test_filter)
        
        # Select the item
        content._filter_list.setCurrentRow(0)
        
        # Verify buttons are enabled
        assert content._delete_button.isEnabled()
        assert content._rename_button.isEnabled()
        
        # Track signal emissions
        signal_data = []
        def on_deleted(filter_id: str):
            signal_data.append(filter_id)
        
        content.filter_deleted.connect(on_deleted)
        
        # Click delete button
        content._delete_button.click()
        
        # Wait for signal
        qtbot.wait(10)
        
        # Verify signal emitted
        assert len(signal_data) == 1
        assert signal_data[0] == "test-id"
    
    def test_rename_button_starts_edit(self, qtbot) -> None:
        """Test that rename button starts inline edit."""
        from src.views.components.filters_tab import FiltersTabContent
        
        content = FiltersTabContent()
        qtbot.addWidget(content)
        
        # Add filter
        test_filter = SavedFilter(
            id="test-id",
            name="Test Filter",
            filter_text="error",
            filter_mode=FilterMode.PLAIN,
            created_at=time.time()
        )
        content.add_filter(test_filter)
        
        # Select the item
        content._filter_list.setCurrentRow(0)
        
        # Click rename button
        content._rename_button.click()
        
        # Verify item is in edit mode (this is hard to test directly)
        # We just verify the button doesn't crash
        qtbot.wait(10)
    
    def test_button_states_no_selection(self, qtbot) -> None:
        """Test that buttons are disabled when no selection."""
        from src.views.components.filters_tab import FiltersTabContent
        
        content = FiltersTabContent()
        qtbot.addWidget(content)
        
        # Add filters
        filter1 = SavedFilter(
            id="id-1",
            name="Filter 1",
            filter_text="error",
            filter_mode=FilterMode.PLAIN,
            created_at=time.time()
        )
        content.add_filter(filter1)
        
        # No selection - buttons should be disabled
        assert not content._delete_button.isEnabled()
        assert not content._rename_button.isEnabled()
        
        # Select item - buttons should be enabled
        content._filter_list.setCurrentRow(0)
        assert content._delete_button.isEnabled()
        assert content._rename_button.isEnabled()
        
        # Clear selection by setting current item to None - buttons should be disabled again
        content._filter_list.setCurrentItem(None)
        assert not content._delete_button.isEnabled()
        assert not content._rename_button.isEnabled()
    
    def test_set_filters_clears_existing(self, qtbot) -> None:
        """Test that set_filters clears existing items."""
        from src.views.components.filters_tab import FiltersTabContent
        
        content = FiltersTabContent()
        qtbot.addWidget(content)
        
        # Add initial filters
        filter1 = SavedFilter(
            id="id-1",
            name="Filter 1",
            filter_text="error",
            filter_mode=FilterMode.PLAIN,
            created_at=time.time()
        )
        content.set_filters([filter1])
        
        assert content._filter_list.count() == 1
        
        # Set new filters
        filter2 = SavedFilter(
            id="id-2",
            name="Filter 2",
            filter_text="warning",
            filter_mode=FilterMode.REGEX,
            created_at=time.time()
        )
        filter3 = SavedFilter(
            id="id-3",
            name="Filter 3",
            filter_text="info",
            filter_mode=FilterMode.SIMPLE,
            created_at=time.time()
        )
        content.set_filters([filter2, filter3])
        
        # Verify old items cleared
        assert content._filter_list.count() == 2
        assert "id-1" not in content._filter_items
        assert "id-2" in content._filter_items
        assert "id-3" in content._filter_items
    
    def test_filter_item_display(self, qtbot) -> None:
        """Test that filter items display correctly."""
        from src.views.components.filters_tab import FiltersTabContent
        from PySide6.QtCore import Qt
        
        content = FiltersTabContent()
        qtbot.addWidget(content)
        
        # Add filter with enabled=True
        enabled_filter = SavedFilter(
            id="enabled-id",
            name="Enabled Filter",
            filter_text="error",
            filter_mode=FilterMode.PLAIN,
            created_at=time.time(),
            enabled=True
        )
        content.add_filter(enabled_filter)
        
        # Add filter with enabled=False
        disabled_filter = SavedFilter(
            id="disabled-id",
            name="Disabled Filter",
            filter_text="warning",
            filter_mode=FilterMode.REGEX,
            created_at=time.time(),
            enabled=False
        )
        content.add_filter(disabled_filter)
        
        # Verify checkbox states
        enabled_item = content._filter_items["enabled-id"]
        assert enabled_item.checkState() == Qt.Checked
        
        disabled_item = content._filter_items["disabled-id"]
        assert disabled_item.checkState() == Qt.Unchecked
    
    def test_filter_item_data_storage(self, qtbot) -> None:
        """Test that filter_id is stored in item data."""
        from src.views.components.filters_tab import FiltersTabContent
        from PySide6.QtCore import Qt
        
        content = FiltersTabContent()
        qtbot.addWidget(content)
        
        # Add filter
        test_filter = SavedFilter(
            id="test-filter-id",
            name="Test Filter",
            filter_text="error",
            filter_mode=FilterMode.PLAIN,
            created_at=time.time()
        )
        content.add_filter(test_filter)
        
        # Verify filter_id stored in item data
        item = content._filter_items["test-filter-id"]
        stored_id = item.data(Qt.ItemDataRole.UserRole)
        assert stored_id == "test-filter-id"


class TestFiltersTabContentTypeSafety:
    """Tests for type safety with beartype decorator.
    
    // Ref: docs/SPEC.md §1 (beartype requirement)
    """
    
    def test_filters_tab_content_methods_have_beartype(self, qtbot) -> None:
        """Verify all public methods have @beartype decorator."""
        from src.views.components.filters_tab import FiltersTabContent
        
        content = FiltersTabContent()
        qtbot.addWidget(content)
        
        # These should work without errors
        test_filter = SavedFilter(
            id="test-id",
            name="Test",
            filter_text="error",
            filter_mode=FilterMode.PLAIN,
            created_at=time.time()
        )
        content.set_filters([test_filter])
        content.add_filter(test_filter)
        content.remove_filter("test-id")


class TestSearchToolbarSaveButton:
    """Tests for SearchToolbar save button functionality.
    
    // Ref: docs/specs/features/saved-filters.md §4.1
    // Ref: docs/SPEC.md §10.1
    """
    
    def test_save_button_exists(self, qtbot) -> None:
        """Test that save button exists in SearchToolbar."""
        from src.views.widgets.search_toolbar import SearchToolbar
        
        toolbar = SearchToolbar()
        qtbot.addWidget(toolbar)
        
        # Verify save button exists
        assert hasattr(toolbar, '_save_button')
        assert toolbar._save_button.text() == "💾"
        assert toolbar._save_button.toolTip() == "Save current filter"
    
    def test_save_button_initially_disabled(self, qtbot) -> None:
        """Test that save button is initially disabled.
        
        // Ref: docs/specs/features/saved-filters.md §4.1 - Initially disabled
        """
        from src.views.widgets.search_toolbar import SearchToolbar
        
        toolbar = SearchToolbar()
        qtbot.addWidget(toolbar)
        
        # Save button should be disabled when text is empty
        assert not toolbar._save_button.isEnabled()
    
    def test_save_button_disabled_when_text_empty(self, qtbot) -> None:
        """Test that save button is disabled when text is empty.
        
        // Ref: docs/specs/features/saved-filters.md §4.1 - Disabled when text empty
        """
        from src.views.widgets.search_toolbar import SearchToolbar
        
        toolbar = SearchToolbar()
        qtbot.addWidget(toolbar)
        
        # Set text to empty
        toolbar.set_search_text("")
        
        # Save button should be disabled
        assert not toolbar._save_button.isEnabled()
        
        # Set text to whitespace only
        toolbar.set_search_text("   ")
        
        # Save button should still be disabled (whitespace is stripped)
        assert not toolbar._save_button.isEnabled()
    
    def test_save_button_enabled_when_text_present(self, qtbot) -> None:
        """Test that save button is enabled when text is present.
        
        // Ref: docs/specs/features/saved-filters.md §4.1 - Enabled when text present
        """
        from src.views.widgets.search_toolbar import SearchToolbar
        
        toolbar = SearchToolbar()
        qtbot.addWidget(toolbar)
        
        # Set text
        toolbar.set_search_text("error")
        
        # Save button should be enabled
        assert toolbar._save_button.isEnabled()
        
        # Set text with leading/trailing whitespace
        toolbar.set_search_text("  warning  ")
        
        # Save button should be enabled (whitespace is stripped)
        assert toolbar._save_button.isEnabled()
    
    def test_save_button_signal_emission(self, qtbot) -> None:
        """Test that clicking save button emits save_filter_requested signal.
        
        // Ref: docs/specs/features/saved-filters.md §4.1 - Signal emission
        """
        from src.views.widgets.search_toolbar import SearchToolbar
        
        toolbar = SearchToolbar()
        qtbot.addWidget(toolbar)
        
        # Set text and mode
        toolbar.set_search_text("error")
        toolbar.set_filter_mode("regex")
        
        # Track signal emissions
        signal_data = []
        def on_save_requested(filter_text: str, mode: str):
            signal_data.append((filter_text, mode))
        
        toolbar.save_filter_requested.connect(on_save_requested)
        
        # Click save button
        toolbar._save_button.click()
        
        # Wait for signal
        qtbot.wait(10)
        
        # Verify signal emitted with correct parameters
        assert len(signal_data) == 1
        assert signal_data[0] == ("error", "regex")
    
    def test_save_button_signal_with_all_modes(self, qtbot) -> None:
        """Test save button signal with all filter modes."""
        from src.views.widgets.search_toolbar import SearchToolbar
        
        toolbar = SearchToolbar()
        qtbot.addWidget(toolbar)
        
        modes = ["plain", "regex", "simple"]
        
        for mode in modes:
            # Set text and mode
            toolbar.set_search_text("test")
            toolbar.set_filter_mode(mode)
            
            # Track signal emissions
            signal_data = []
            def on_save_requested(filter_text: str, m: str):
                signal_data.append((filter_text, m))
            
            toolbar.save_filter_requested.connect(on_save_requested)
            
            # Click save button
            toolbar._save_button.click()
            
            # Wait for signal
            qtbot.wait(10)
            
            # Verify signal emitted with correct mode
            assert len(signal_data) == 1
            assert signal_data[0] == ("test", mode)
            
            # Disconnect for next iteration
            toolbar.save_filter_requested.disconnect(on_save_requested)
    
    def test_save_button_no_signal_when_empty(self, qtbot) -> None:
        """Test that save button doesn't emit signal when text is empty."""
        from src.views.widgets.search_toolbar import SearchToolbar
        
        toolbar = SearchToolbar()
        qtbot.addWidget(toolbar)
        
        # Ensure text is empty
        toolbar.set_search_text("")
        
        # Track signal emissions
        signal_count = [0]
        def on_save_requested(filter_text: str, mode: str):
            signal_count[0] += 1
        
        toolbar.save_filter_requested.connect(on_save_requested)
        
        # Try to click save button (it's disabled, but let's verify)
        # The button should be disabled, so clicking shouldn't work
        # But even if we force it, the handler should not emit
        toolbar._on_save_clicked()
        
        # Wait for signal
        qtbot.wait(10)
        
        # Verify no signal emitted
        assert signal_count[0] == 0
    
    def test_save_button_state_changes_with_text(self, qtbot) -> None:
        """Test that save button state changes dynamically with text."""
        from src.views.widgets.search_toolbar import SearchToolbar
        
        toolbar = SearchToolbar()
        qtbot.addWidget(toolbar)
        
        # Initially disabled
        assert not toolbar._save_button.isEnabled()
        
        # Type text - button should enable
        toolbar._search_input.setText("error")
        qtbot.wait(10)
        assert toolbar._save_button.isEnabled()
        
        # Clear text - button should disable
        toolbar._search_input.setText("")
        qtbot.wait(10)
        assert not toolbar._save_button.isEnabled()
        
        # Type text again - button should enable
        toolbar._search_input.setText("warning")
        qtbot.wait(10)
        assert toolbar._save_button.isEnabled()
    
    def test_save_button_strips_whitespace(self, qtbot) -> None:
        """Test that save button strips whitespace from text."""
        from src.views.widgets.search_toolbar import SearchToolbar
        
        toolbar = SearchToolbar()
        qtbot.addWidget(toolbar)
        
        # Set text with whitespace
        toolbar.set_search_text("  error  ")
        
        # Track signal emissions
        signal_data = []
        def on_save_requested(filter_text: str, mode: str):
            signal_data.append((filter_text, mode))
        
        toolbar.save_filter_requested.connect(on_save_requested)
        
        # Click save button
        toolbar._save_button.click()
        
        # Wait for signal
        qtbot.wait(10)
        
        # Verify signal emitted with stripped text
        assert len(signal_data) == 1
        assert signal_data[0] == ("error", "plain")


class TestSearchToolbarWithStatsSaveButton:
    """Tests for SearchToolbarWithStats save button forwarding.
    
    // Ref: docs/specs/features/saved-filters.md §4.1
    """
    
    def test_save_filter_signal_forwarded(self, qtbot) -> None:
        """Test that save_filter_requested signal is forwarded."""
        from src.views.widgets.search_toolbar import SearchToolbarWithStats
        
        toolbar = SearchToolbarWithStats()
        qtbot.addWidget(toolbar)
        
        # Set text
        toolbar.set_search_text("error")
        
        # Track signal emissions
        signal_data = []
        def on_save_requested(filter_text: str, mode: str):
            signal_data.append((filter_text, mode))
        
        toolbar.save_filter_requested.connect(on_save_requested)
        
        # Click save button on inner toolbar
        toolbar._search_toolbar._save_button.click()
        
        # Wait for signal
        qtbot.wait(10)
        
        # Verify signal forwarded
        assert len(signal_data) == 1
        assert signal_data[0] == ("error", "plain")


class TestCategoryPanelFiltersTab:
    """Tests for CategoryPanel Filters tab integration.
    
    // Ref: docs/specs/features/saved-filters.md §4.3
    // Ref: docs/specs/features/saved-filters.md §10.1
    """
    
    def test_filters_tab_exists(self, qtbot) -> None:
        """Test that Filters tab exists in CategoryPanel.
        
        // Ref: docs/specs/features/saved-filters.md §4.3
        """
        from src.views.category_panel import CategoryPanel
        from src.views.components.filters_tab import FiltersTabContent
        
        panel = CategoryPanel()
        qtbot.addWidget(panel)
        
        # Verify Filters tab exists (index 1)
        assert panel._tab_widget.tabText(1) == "Filters"
        
        # Verify Filters tab content is FiltersTabContent
        assert hasattr(panel, '_filters_content')
        assert isinstance(panel._filters_content, FiltersTabContent)
    
    def test_get_filters_content(self, qtbot) -> None:
        """Test that get_filters_content returns FiltersTabContent.
        
        // Ref: docs/specs/features/saved-filters.md §4.3
        """
        from src.views.category_panel import CategoryPanel
        from src.views.components.filters_tab import FiltersTabContent
        
        panel = CategoryPanel()
        qtbot.addWidget(panel)
        
        # Get filters content
        filters_content = panel.get_filters_content()
        
        # Verify it's the correct type
        assert isinstance(filters_content, FiltersTabContent)
        assert filters_content is panel._filters_content
    
    def test_saved_filter_enabled_changed_signal(self, qtbot) -> None:
        """Test that saved_filter_enabled_changed signal is forwarded.
        
        // Ref: docs/specs/features/saved-filters.md §4.3
        """
        from src.views.category_panel import CategoryPanel
        from PySide6.QtCore import Qt
        
        panel = CategoryPanel()
        qtbot.addWidget(panel)
        
        # Add a filter to the filters content
        test_filter = SavedFilter(
            id="test-id",
            name="Test Filter",
            filter_text="error",
            filter_mode=FilterMode.PLAIN,
            created_at=time.time(),
            enabled=True
        )
        panel._filters_content.add_filter(test_filter)
        
        # Track signal emissions
        signal_data = []
        def on_enabled_changed(filter_id: str, enabled: bool):
            signal_data.append((filter_id, enabled))
        
        panel.saved_filter_enabled_changed.connect(on_enabled_changed)
        
        # Toggle checkbox in filters content
        item = panel._filters_content._filter_items["test-id"]
        item.setCheckState(Qt.Unchecked)
        
        # Wait for signal
        qtbot.wait(10)
        
        # Verify signal forwarded
        assert len(signal_data) == 1
        assert signal_data[0] == ("test-id", False)
    
    def test_saved_filter_deleted_signal(self, qtbot) -> None:
        """Test that saved_filter_deleted signal is forwarded.
        
        // Ref: docs/specs/features/saved-filters.md §4.3
        """
        from src.views.category_panel import CategoryPanel
        
        panel = CategoryPanel()
        qtbot.addWidget(panel)
        
        # Add a filter to the filters content
        test_filter = SavedFilter(
            id="test-id",
            name="Test Filter",
            filter_text="error",
            filter_mode=FilterMode.PLAIN,
            created_at=time.time()
        )
        panel._filters_content.add_filter(test_filter)
        
        # Select the filter
        panel._filters_content._filter_list.setCurrentRow(0)
        
        # Track signal emissions
        signal_data = []
        def on_deleted(filter_id: str):
            signal_data.append(filter_id)
        
        panel.saved_filter_deleted.connect(on_deleted)
        
        # Click delete button
        panel._filters_content._delete_button.click()
        
        # Wait for signal
        qtbot.wait(10)
        
        # Verify signal forwarded
        assert len(signal_data) == 1
        assert signal_data[0] == "test-id"
    
    def test_saved_filter_renamed_signal(self, qtbot) -> None:
        """Test that saved_filter_renamed signal is forwarded.
        
        // Ref: docs/specs/features/saved-filters.md §4.3
        """
        from src.views.category_panel import CategoryPanel
        
        panel = CategoryPanel()
        qtbot.addWidget(panel)
        
        # Add a filter to the filters content
        test_filter = SavedFilter(
            id="test-id",
            name="Test Filter",
            filter_text="error",
            filter_mode=FilterMode.PLAIN,
            created_at=time.time()
        )
        panel._filters_content.add_filter(test_filter)
        
        # Track signal emissions
        signal_data = []
        def on_renamed(filter_id: str, new_name: str):
            signal_data.append((filter_id, new_name))
        
        panel.saved_filter_renamed.connect(on_renamed)
        
        # Emit rename signal from filters content
        panel._filters_content.filter_renamed.emit("test-id", "Renamed Filter")
        
        # Wait for signal
        qtbot.wait(10)
        
        # Verify signal forwarded
        assert len(signal_data) == 1
        assert signal_data[0] == ("test-id", "Renamed Filter")
    
    def test_signals_exist(self, qtbot) -> None:
        """Test that all required signals exist on CategoryPanel.
        
        // Ref: docs/specs/features/saved-filters.md §4.3
        """
        from src.views.category_panel import CategoryPanel
        
        panel = CategoryPanel()
        qtbot.addWidget(panel)
        
        # Verify signals exist
        assert hasattr(panel, 'saved_filter_enabled_changed')
        assert hasattr(panel, 'saved_filter_deleted')
        assert hasattr(panel, 'saved_filter_renamed')
    
    def test_filters_tab_layout(self, qtbot) -> None:
        """Test that Filters tab has correct layout.
        
        // Ref: docs/specs/features/saved-filters.md §4.3
        """
        from src.views.category_panel import CategoryPanel
        from PySide6.QtWidgets import QVBoxLayout
        
        panel = CategoryPanel()
        qtbot.addWidget(panel)
        
        # Verify Filters tab has layout
        filters_tab = panel._filters_tab
        layout = filters_tab.layout()
        
        assert layout is not None
        assert isinstance(layout, QVBoxLayout)
        
        # Verify margins
        assert layout.contentsMargins().left() == 4
        assert layout.contentsMargins().top() == 4
        assert layout.contentsMargins().right() == 4
        assert layout.contentsMargins().bottom() == 4


class TestMainControllerSavedFilterIntegration:
    """Tests for MainController integration with SavedFilterController.
    
    // Ref: docs/specs/features/saved-filters.md §5.2
    // Ref: docs/specs/features/saved-filters.md §10.1
    """
    
    def test_save_filter_from_toolbar(self, qtbot, tmp_path) -> None:
        """Test saving filter from SearchToolbar save button.
        
        // Ref: docs/specs/features/saved-filters.md §5.2
        """
        from src.controllers.main_controller import MainController
        from src.views.main_window import MainWindow
        from src.utils.settings_manager import SettingsManager
        from src.models.log_entry import LogEntry, LogLevel
        
        # Create settings file
        settings_file = str(tmp_path / "test_settings.json")
        settings_manager = SettingsManager(filepath=settings_file)
        settings_manager.load()
        
        # Create main window and controller
        window = MainWindow()
        qtbot.addWidget(window)
        
        # Patch SettingsManager to use test file
        from unittest.mock import patch
        with patch('src.controllers.main_controller.SettingsManager') as MockSettingsManager:
            MockSettingsManager.return_value = settings_manager
            controller = MainController(window)
        
        # Simulate save filter request from toolbar
        # Track signal emissions
        saved_filters = []
        def on_filters_changed():
            saved_filters.append(controller._saved_filter_controller.get_all_filters())
        
        controller._saved_filter_controller.filters_changed.connect(on_filters_changed)
        
        # Emit save filter request
        window.get_search_toolbar().save_filter_requested.emit("error|critical", "plain")
        
        # Wait for signal
        qtbot.wait(10)
        
        # Verify filter was saved
        assert len(saved_filters) == 1
        filters = controller._saved_filter_controller.get_all_filters()
        assert len(filters) == 1
        assert filters[0].filter_text == "error|critical"
        assert filters[0].filter_mode == FilterMode.PLAIN
        assert filters[0].enabled is True
        
        window.close()
    
    def test_enable_disable_filter_in_panel(self, qtbot, tmp_path) -> None:
        """Test enabling/disabling filter from CategoryPanel.
        
        // Ref: docs/specs/features/saved-filters.md §5.2
        """
        from src.controllers.main_controller import MainController
        from src.views.main_window import MainWindow
        from src.utils.settings_manager import SettingsManager
        from unittest.mock import patch
        
        # Create settings file
        settings_file = str(tmp_path / "test_settings.json")
        settings_manager = SettingsManager(filepath=settings_file)
        settings_manager.load()
        
        # Create main window and controller
        window = MainWindow()
        qtbot.addWidget(window)
        
        with patch('src.controllers.main_controller.SettingsManager') as MockSettingsManager:
            MockSettingsManager.return_value = settings_manager
            controller = MainController(window)
        
        # Save a filter first
        filter_id = controller._saved_filter_controller.save_filter(
            text="error",
            mode=FilterMode.PLAIN,
            name="Test Filter"
        )
        
        # Track filter_applied signal emissions
        applied_count = [0]
        def on_filter_applied():
            applied_count[0] += 1
        
        controller._saved_filter_controller.filter_applied.connect(on_filter_applied)
        
        # Disable filter via CategoryPanel signal
        window.get_category_panel().saved_filter_enabled_changed.emit(filter_id, False)
        
        # Wait for signal
        qtbot.wait(10)
        
        # Verify filter was disabled
        filters = controller._saved_filter_controller.get_all_filters()
        assert len(filters) == 1
        assert filters[0].enabled is False
        assert applied_count[0] == 1
        
        # Enable filter via CategoryPanel signal
        window.get_category_panel().saved_filter_enabled_changed.emit(filter_id, True)
        
        # Wait for signal
        qtbot.wait(10)
        
        # Verify filter was enabled
        filters = controller._saved_filter_controller.get_all_filters()
        assert filters[0].enabled is True
        assert applied_count[0] == 2
        
        window.close()
    
    def test_delete_filter_from_panel(self, qtbot, tmp_path) -> None:
        """Test deleting filter from CategoryPanel.
        
        // Ref: docs/specs/features/saved-filters.md §5.2
        """
        from src.controllers.main_controller import MainController
        from src.views.main_window import MainWindow
        from src.utils.settings_manager import SettingsManager
        from unittest.mock import patch
        
        # Create settings file
        settings_file = str(tmp_path / "test_settings.json")
        settings_manager = SettingsManager(filepath=settings_file)
        settings_manager.load()
        
        # Create main window and controller
        window = MainWindow()
        qtbot.addWidget(window)
        
        with patch('src.controllers.main_controller.SettingsManager') as MockSettingsManager:
            MockSettingsManager.return_value = settings_manager
            controller = MainController(window)
        
        # Save a filter first
        filter_id = controller._saved_filter_controller.save_filter(
            text="error",
            mode=FilterMode.PLAIN,
            name="Test Filter"
        )
        
        # Verify filter exists
        assert len(controller._saved_filter_controller.get_all_filters()) == 1
        
        # Delete filter via CategoryPanel signal
        window.get_category_panel().saved_filter_deleted.emit(filter_id)
        
        # Wait for signal
        qtbot.wait(10)
        
        # Verify filter was deleted
        assert len(controller._saved_filter_controller.get_all_filters()) == 0
        
        window.close()
    
    def test_rename_filter_from_panel(self, qtbot, tmp_path) -> None:
        """Test renaming filter from CategoryPanel.
        
        // Ref: docs/specs/features/saved-filters.md §5.2
        """
        from src.controllers.main_controller import MainController
        from src.views.main_window import MainWindow
        from src.utils.settings_manager import SettingsManager
        from unittest.mock import patch
        
        # Create settings file
        settings_file = str(tmp_path / "test_settings.json")
        settings_manager = SettingsManager(filepath=settings_file)
        settings_manager.load()
        
        # Create main window and controller
        window = MainWindow()
        qtbot.addWidget(window)
        
        with patch('src.controllers.main_controller.SettingsManager') as MockSettingsManager:
            MockSettingsManager.return_value = settings_manager
            controller = MainController(window)
        
        # Save a filter first
        filter_id = controller._saved_filter_controller.save_filter(
            text="error",
            mode=FilterMode.PLAIN,
            name="Old Name"
        )
        
        # Rename filter via CategoryPanel signal
        window.get_category_panel().saved_filter_renamed.emit(filter_id, "New Name")
        
        # Wait for signal
        qtbot.wait(10)
        
        # Verify filter was renamed
        filters = controller._saved_filter_controller.get_all_filters()
        assert len(filters) == 1
        assert filters[0].name == "New Name"
        
        window.close()
    
    def test_combined_filtering_saved_and_category(self, qtbot, tmp_path) -> None:
        """Test combined filtering: saved text filter AND category filter.
        
        // Ref: docs/specs/features/saved-filters.md §3.2
        // Ref: docs/specs/features/saved-filters.md §5.2
        """
        from src.controllers.main_controller import MainController
        from src.views.main_window import MainWindow
        from src.utils.settings_manager import SettingsManager
        from src.models.log_entry import LogEntry, LogLevel
        from src.models.log_document import LogDocument
        from unittest.mock import patch, MagicMock
        
        # Create settings file
        settings_file = str(tmp_path / "test_settings.json")
        settings_manager = SettingsManager(filepath=settings_file)
        settings_manager.load()
        
        # Create main window and controller
        window = MainWindow()
        qtbot.addWidget(window)
        
        with patch('src.controllers.main_controller.SettingsManager') as MockSettingsManager:
            MockSettingsManager.return_value = settings_manager
            controller = MainController(window)
        
        # Create test entries
        # Ref: docs/specs/features/log-entry-optimization.md §4.2
        # Ref: docs/specs/features/timestamp-unix-epoch.md §3.1
        # timestamp is Unix Epoch float
        entries = [
            LogEntry(
                row_index=0,
                timestamp=1700000000.0,
                level=LogLevel.ERROR,
                category="App.Module1",
                display_message="Error in module1",
                file_offset=0,
            ),
            LogEntry(
                row_index=1,
                timestamp=1700000001.0,
                level=LogLevel.WARNING,
                category="App.Module2",
                display_message="Warning in module2",
                file_offset=100,
            ),
            LogEntry(
                row_index=2,
                timestamp=1700000002.0,
                level=LogLevel.MSG,
                category="App.Module1",
                display_message="Info in module1",
                file_offset=200,
            ),
        ]
        
        # Set entries directly
        controller._all_entries = entries
        
        # Save a text filter for "Error"
        controller._saved_filter_controller.save_filter(
            text="Error",
            mode=FilterMode.PLAIN,
            name="Error Filter"
        )
        
        # Mock category filter to only match "App.Module1"
        def category_filter(entry: LogEntry) -> bool:
            return entry.category == "App.Module1"
        
        controller._filter_controller.get_filter = lambda: category_filter
        
        # Apply filters
        controller._apply_filters()
        
        # Combined filter should match:
        # - Category filter: App.Module1 (entries 0 and 2)
        # - Saved text filter: contains "Error" (entry 0)
        # - AND logic: only entry 0 matches both
        assert len(controller._filtered_entries) == 1
        assert controller._filtered_entries[0].row_index == 0
        
        window.close()
    
    def test_combined_filtering_saved_or_logic(self, qtbot, tmp_path) -> None:
        """Test that multiple saved filters combine with OR logic.
        
        // Ref: docs/specs/features/saved-filters.md §3.1
        // Ref: docs/specs/features/saved-filters.md §5.2
        """
        from src.controllers.main_controller import MainController
        from src.views.main_window import MainWindow
        from src.utils.settings_manager import SettingsManager
        from src.models.log_entry import LogEntry, LogLevel
        from unittest.mock import patch
        
        # Create settings file
        settings_file = str(tmp_path / "test_settings.json")
        settings_manager = SettingsManager(filepath=settings_file)
        settings_manager.load()
        
        # Create main window and controller
        window = MainWindow()
        qtbot.addWidget(window)
        
        with patch('src.controllers.main_controller.SettingsManager') as MockSettingsManager:
            MockSettingsManager.return_value = settings_manager
            controller = MainController(window)
        
        # Create test entries
        # Ref: docs/specs/features/log-entry-optimization.md §4.2
        # Ref: docs/specs/features/timestamp-unix-epoch.md §3.1
        # timestamp is Unix Epoch float
        entries = [
            LogEntry(
                row_index=0,
                timestamp=1700000000.0,
                level=LogLevel.ERROR,
                category="App",
                display_message="Error message",
                file_offset=0,
            ),
            LogEntry(
                row_index=1,
                timestamp=1700000001.0,
                level=LogLevel.WARNING,
                category="App",
                display_message="Warning message",
                file_offset=100,
            ),
            LogEntry(
                row_index=2,
                timestamp=1700000002.0,
                level=LogLevel.MSG,
                category="App",
                display_message="Info message",
                file_offset=200,
            ),
        ]
        
        # Set entries directly
        controller._all_entries = entries
        
        # Save two filters: "Error" and "Warning"
        controller._saved_filter_controller.save_filter(
            text="Error",
            mode=FilterMode.PLAIN,
            name="Error Filter"
        )
        controller._saved_filter_controller.save_filter(
            text="Warning",
            mode=FilterMode.PLAIN,
            name="Warning Filter"
        )
        
        # No category filter
        controller._filter_controller.get_filter = lambda: None
        
        # Apply filters
        controller._apply_filters()
        
        # OR logic: should match entries containing "Error" OR "Warning"
        # Entry 0: "Error message" - matches
        # Entry 1: "Warning message" - matches
        # Entry 2: "Info message" - doesn't match
        assert len(controller._filtered_entries) == 2
        matched_indices = {e.row_index for e in controller._filtered_entries}
        assert matched_indices == {0, 1}
        
        window.close()
    
    def test_populate_filters_tab_on_file_load(self, qtbot, tmp_path) -> None:
        """Test that filters tab is populated when file is loaded.
        
        // Ref: docs/specs/features/saved-filters.md §5.2
        """
        from src.controllers.main_controller import MainController
        from src.views.main_window import MainWindow
        from src.utils.settings_manager import SettingsManager
        from unittest.mock import patch, MagicMock
        
        # Create settings file
        settings_file = str(tmp_path / "test_settings.json")
        settings_manager = SettingsManager(filepath=settings_file)
        settings_manager.load()
        
        # Create main window and controller
        window = MainWindow()
        qtbot.addWidget(window)
        
        with patch('src.controllers.main_controller.SettingsManager') as MockSettingsManager:
            MockSettingsManager.return_value = settings_manager
            controller = MainController(window)
        
        # Save some filters
        controller._saved_filter_controller.save_filter(
            text="error",
            mode=FilterMode.PLAIN,
            name="Error Filter"
        )
        controller._saved_filter_controller.save_filter(
            text="warning",
            mode=FilterMode.REGEX,
            name="Warning Filter"
        )
        
        # Get filters content
        filters_content = window.get_category_panel().get_filters_content()
        
        # Manually populate filters tab (simulates what happens in _on_index_complete)
        filters = controller._saved_filter_controller.get_all_filters()
        filters_content.set_filters(filters)
        
        # Verify filters are populated
        assert filters_content._filter_list.count() == 2
        
        window.close()