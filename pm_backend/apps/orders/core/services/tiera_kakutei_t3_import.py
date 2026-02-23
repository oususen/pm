from .tiera_kakutei_import import TieraKakuteiImportService


class TieraKakuteiT3ImportService(TieraKakuteiImportService):
    """ティエラ確定(T3)専用インポートサービス"""
    EXPECTED_SUPPLIER_CODE = 'E820T3'

    def import_csv(self, file, customer_code, order_type, source_system='CSV'):
        filename_upper = (file.name or '').upper()
        if '_T3' not in filename_upper:
            return {
                'success': False,
                'message': 'T3取込はファイル名に「_T3」が必要です',
                'errors': [f'ファイル名チェックエラー: {file.name}'],
                'warnings': ['T3取込を選択した場合、ファイル名末尾に _T3 を付けてください。'],
            }

        t3_source_system = source_system.strip() if source_system else 'CSV'
        if 'T3' not in t3_source_system.upper():
            t3_source_system = f'{t3_source_system}-T3'
        return super().import_csv(file, customer_code, order_type, t3_source_system)
