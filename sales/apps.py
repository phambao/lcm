from django.apps import AppConfig

PO_FORMULA_CONTENT_TYPE = None
DATA_ENTRY_CONTENT_TYPE = None
UNIT_LIBRARY_CONTENT_TYPE = None
DESCRIPTION_LIBRARY_CONTENT_TYPE = None
ASSEMBLE_CONTENT_TYPE = None
ESTIMATE_TEMPLATE_CONTENT_TYPE = None


class SalesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'sales'

    def ready(self):
        """
        Content type is already cache, so no need to do this
        """
        from django.contrib.contenttypes.models import ContentType
        from django.db.utils import ProgrammingError
        from sales.models.estimate import POFormula, DataEntry, UnitLibrary, DescriptionLibrary, Assemble, EstimateTemplate

        global PO_FORMULA_CONTENT_TYPE, DATA_ENTRY_CONTENT_TYPE,\
            UNIT_LIBRARY_CONTENT_TYPE, DESCRIPTION_LIBRARY_CONTENT_TYPE,\
            ASSEMBLE_CONTENT_TYPE, ESTIMATE_TEMPLATE_CONTENT_TYPE
        try:
            PO_FORMULA_CONTENT_TYPE = ContentType.objects.get_for_model(POFormula).pk
            DATA_ENTRY_CONTENT_TYPE = ContentType.objects.get_for_model(DataEntry).pk
            UNIT_LIBRARY_CONTENT_TYPE = ContentType.objects.get_for_model(UnitLibrary).pk
            DESCRIPTION_LIBRARY_CONTENT_TYPE = ContentType.objects.get_for_model(DescriptionLibrary).pk
            ASSEMBLE_CONTENT_TYPE = ContentType.objects.get_for_model(Assemble).pk
            ESTIMATE_TEMPLATE_CONTENT_TYPE = ContentType.objects.get_for_model(EstimateTemplate).pk
        except ProgrammingError:
            """Ignore when no table in db, only used for testing"""
