from .csv_import import CSVImportService


class KubotaHirakataNaijiImportService(CSVImportService):
    """Kubota Hirakata Naiji (Forecast) CSV Import Service.

    現在は共通のCSVImportServiceを継承して、標準フォーマットの取込を行います。
    将来、枚方内示固有のレイアウトがわかったらここにパース処理を実装してください。
    """
    pass
