"""未保存の分析案をRedisで共有し、期限と承認版を照合する。"""
import json
from copy import deepcopy
from datetime import datetime, timedelta
from uuid import uuid4

from django.conf import settings
from redis import Redis
from redis.exceptions import RedisError, WatchError
from rest_framework.exceptions import APIException


class AnalysisError(APIException):
    def __init__(self, detail, status=400):
        self.status_code = status
        super().__init__(detail)


class AnalysisPlanStore:
    def __init__(self):
        if not settings.AI_ANALYSIS_REDIS_URL:
            raise AnalysisError('分析案用Redisの接続先が未設定です。管理者へ確認してください。', 503)
        self.client = Redis.from_url(settings.AI_ANALYSIS_REDIS_URL, decode_responses=True)

    def _key(self, plan_id):
        return f'pm:ai:analysis:plan:{plan_id}'

    def check_connection(self):
        try:
            self.client.ping()
        except RedisError as exc:
            raise AnalysisError('分析案用Redisへ接続できません。分析案は保存されていません。', 503) from exc

    def create(self, owner_id, proposal, ttl_minutes):
        now = datetime.now()
        plan = {
            'id': str(uuid4()), 'owner_id': owner_id, 'revision': 1,
            'status': 'awaiting_method', 'proposal': proposal,
            'created_at': now.isoformat(),
            'expires_at': (now + timedelta(minutes=ttl_minutes)).isoformat(),
            'method_approved_at': None, 'data_approved_at': None, 'preview': None,
        }
        try:
            saved = self.client.set(self._key(plan['id']), json.dumps(plan, ensure_ascii=False), ex=ttl_minutes * 60, nx=True)
            if not saved:
                raise AnalysisError('分析案を保存できませんでした。再作成してください。', 503)
        except RedisError as exc:
            raise AnalysisError('分析案用Redisへ保存できませんでした。', 503) from exc
        return plan

    @staticmethod
    def _decode(raw, owner_id):
        if raw is None:
            raise AnalysisError('分析案の期限が切れたか、保持先が再起動しました。分析案を作り直してください。', 410)
        plan = json.loads(raw)
        if plan['owner_id'] != owner_id:
            raise AnalysisError('分析案が見つかりません。', 404)
        return plan

    def get(self, plan_id, owner_id):
        try:
            return self._decode(self.client.get(self._key(plan_id)), owner_id)
        except RedisError as exc:
            raise AnalysisError('分析案用Redisへ接続できません。', 503) from exc

    def update(self, plan_id, owner_id, revision, change):
        if type(revision) is not int or revision < 1:
            raise AnalysisError('分析案の版が不正です。')
        key = self._key(plan_id)
        try:
            with self.client.pipeline() as pipe:
                pipe.watch(key)
                plan = self._decode(pipe.get(key), owner_id)
                if plan['revision'] != revision:
                    raise AnalysisError('分析案が別の操作で更新されました。最新の内容を確認してください。', 409)
                updated = deepcopy(plan)
                change(updated)
                updated['revision'] += 1
                pipe.multi()
                # 承認しても有効期限を延長せず、消えたキーを再作成しない。
                pipe.set(key, json.dumps(updated, ensure_ascii=False), xx=True, keepttl=True)
                if not pipe.execute()[0]:
                    raise AnalysisError('分析案の期限が切れました。再作成してください。', 410)
                return updated
        except WatchError as exc:
            raise AnalysisError('分析案が更新または期限切れになりました。最新の内容を確認してください。', 409) from exc
        except RedisError as exc:
            raise AnalysisError('分析案用Redisへ保存できませんでした。', 503) from exc


def public_plan(plan):
    """利用者IDは画面に不要なため返却しない。"""
    return {key: value for key, value in plan.items() if key != 'owner_id'}
