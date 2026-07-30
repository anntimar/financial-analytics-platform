import uuid
from datetime import date
from typing import Any, cast

import httpx


class DashboardAPIError(Exception):
    pass


class FinAnalyticsClient:
    def __init__(
        self,
        base_url: str,
        timeout: float = 15,
        transport: httpx.BaseTransport | None = None,
        access_token: str | None = None,
    ) -> None:
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=timeout,
            transport=transport,
            headers={"Authorization": f"Bearer {access_token}"} if access_token else None,
        )

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        try:
            response = self._client.request(method, path, **kwargs)
            response.raise_for_status()
            if response.status_code == 204:
                return None
            return response.json()
        except httpx.RequestError as exc:
            raise DashboardAPIError(
                "Não foi possível conectar à API. Verifique se o serviço está ativo."
            ) from exc
        except httpx.HTTPStatusError as exc:
            try:
                detail = exc.response.json().get("detail", exc.response.text)
            except ValueError:
                detail = exc.response.text
            raise DashboardAPIError(str(detail)) from exc

    def health(self) -> dict[str, Any]:
        return cast(dict[str, Any], self._request("GET", "/health"))

    def login(self, email: str, password: str) -> dict[str, Any]:
        return cast(
            dict[str, Any],
            self._request("POST", "/auth/login", json={"email": email, "password": password}),
        )

    def companies(self) -> list[dict[str, Any]]:
        response = cast(
            dict[str, Any],
            self._request("GET", "/companies", params={"page": 1, "page_size": 100}),
        )
        return cast(list[dict[str, Any]], response["items"])

    def users(
        self,
        company_id: uuid.UUID | str | None = None,
        active_only: bool = False,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"page": 1, "page_size": 100, "active_only": active_only}
        if company_id:
            params["company_id"] = str(company_id)
        return self._paged_items("/auth/users", **params)

    def create_user(
        self,
        name: str,
        email: str,
        password: str,
        role: str,
        company_id: uuid.UUID | str | None,
    ) -> dict[str, Any]:
        return cast(
            dict[str, Any],
            self._request(
                "POST",
                "/auth/users",
                json={
                    "name": name,
                    "email": email,
                    "password": password,
                    "role": role,
                    "company_id": str(company_id) if company_id else None,
                },
            ),
        )

    def update_user(
        self,
        user_id: uuid.UUID | str,
        *,
        name: str,
        role: str,
        company_id: uuid.UUID | str | None,
        is_active: bool,
    ) -> dict[str, Any]:
        return cast(
            dict[str, Any],
            self._request(
                "PATCH",
                f"/auth/users/{user_id}",
                json={
                    "name": name,
                    "role": role,
                    "company_id": str(company_id) if company_id else None,
                    "is_active": is_active,
                },
            ),
        )

    def user_audit_events(
        self,
        target_user_id: uuid.UUID | str | None = None,
        action: str | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"page": 1, "page_size": 100}
        if target_user_id:
            params["target_user_id"] = str(target_user_id)
        if action:
            params["action"] = action
        return self._paged_items("/auth/audit-events", **params)

    def category_options(self, company_id: uuid.UUID | str) -> list[dict[str, Any]]:
        return self._paged_items("/categories", company_id=company_id, page=1, page_size=100)

    def account_options(self, company_id: uuid.UUID | str) -> list[dict[str, Any]]:
        return self._paged_items(
            "/accounts",
            company_id=company_id,
            page=1,
            page_size=100,
            active_only=True,
        )

    def cost_center_options(self, company_id: uuid.UUID | str) -> list[dict[str, Any]]:
        return self._paged_items("/cost-centers", company_id=company_id, page=1, page_size=100)

    def transactions(
        self,
        company_id: uuid.UUID | str,
        start_date: date,
        end_date: date,
        transaction_type: str | None = None,
        status: str | None = None,
        category_id: uuid.UUID | str | None = None,
        account_id: uuid.UUID | str | None = None,
        cost_center_id: uuid.UUID | str | None = None,
    ) -> dict[str, Any]:
        params = {
            "company_id": str(company_id),
            "page": 1,
            "page_size": 100,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        }
        optional = {
            "transaction_type": transaction_type,
            "status": status,
            "category_id": str(category_id) if category_id else None,
            "account_id": str(account_id) if account_id else None,
            "cost_center_id": str(cost_center_id) if cost_center_id else None,
        }
        params.update({key: value for key, value in optional.items() if value})
        return cast(
            dict[str, Any],
            self._request("GET", "/transactions", params=params),
        )

    def _paged_items(self, path: str, **params: Any) -> list[dict[str, Any]]:
        normalized = {
            key: str(value) if isinstance(value, uuid.UUID) else value
            for key, value in params.items()
        }
        response = cast(dict[str, Any], self._request("GET", path, params=normalized))
        return cast(list[dict[str, Any]], response["items"])

    def executive_summary(
        self, company_id: uuid.UUID | str, start_date: date, end_date: date
    ) -> dict[str, Any]:
        return cast(
            dict[str, Any],
            self._analytics("/analytics/executive-summary", company_id, start_date, end_date),
        )

    def monthly(
        self, company_id: uuid.UUID | str, start_date: date, end_date: date
    ) -> list[dict[str, Any]]:
        return cast(
            list[dict[str, Any]],
            self._analytics("/analytics/monthly", company_id, start_date, end_date),
        )

    def categories(
        self,
        company_id: uuid.UUID | str,
        start_date: date,
        end_date: date,
        transaction_type: str = "expense",
    ) -> list[dict[str, Any]]:
        return cast(
            list[dict[str, Any]],
            self._analytics(
                "/analytics/categories",
                company_id,
                start_date,
                end_date,
                transaction_type=transaction_type,
            ),
        )

    def cash_flow(
        self, company_id: uuid.UUID | str, start_date: date, end_date: date
    ) -> list[dict[str, Any]]:
        return cast(
            list[dict[str, Any]],
            self._analytics("/analytics/cash-flow", company_id, start_date, end_date),
        )

    def cost_centers(
        self, company_id: uuid.UUID | str, start_date: date, end_date: date
    ) -> list[dict[str, Any]]:
        return cast(
            list[dict[str, Any]],
            self._analytics("/analytics/cost-centers", company_id, start_date, end_date),
        )

    def overdue(
        self, company_id: uuid.UUID | str, start_date: date, end_date: date
    ) -> dict[str, Any]:
        return cast(
            dict[str, Any],
            self._analytics("/analytics/overdue", company_id, start_date, end_date),
        )

    def budget_comparison(
        self, company_id: uuid.UUID | str, start_date: date, end_date: date
    ) -> list[dict[str, Any]]:
        return cast(
            list[dict[str, Any]],
            self._analytics("/analytics/budget-comparison", company_id, start_date, end_date),
        )

    def account_balances(
        self, company_id: uuid.UUID | str, start_date: date, end_date: date
    ) -> list[dict[str, Any]]:
        return cast(
            list[dict[str, Any]],
            self._analytics("/analytics/account-balances", company_id, start_date, end_date),
        )

    def alerts(
        self, company_id: uuid.UUID | str, start_date: date, end_date: date
    ) -> list[dict[str, Any]]:
        return cast(
            list[dict[str, Any]],
            self._analytics("/alerts", company_id, start_date, end_date),
        )

    def executive_report(
        self, company_id: uuid.UUID | str, start_date: date, end_date: date
    ) -> dict[str, Any]:
        return cast(
            dict[str, Any],
            self._analytics("/reports/executive", company_id, start_date, end_date),
        )

    def executive_report_csv(
        self, company_id: uuid.UUID | str, start_date: date, end_date: date
    ) -> bytes:
        try:
            response = self._client.get(
                "/reports/executive.csv",
                params={
                    "company_id": str(company_id),
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                },
            )
            response.raise_for_status()
            return response.content
        except httpx.RequestError as exc:
            raise DashboardAPIError(
                "Não foi possível conectar à API. Verifique se o serviço está ativo."
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise DashboardAPIError(exc.response.text) from exc

    def update_alert_action(
        self,
        company_id: uuid.UUID | str,
        alert_code: str,
        reference_date: date,
        period_start: date,
        period_end: date,
        status: str,
        note: str | None,
    ) -> dict[str, Any]:
        return cast(
            dict[str, Any],
            self._request(
                "PUT",
                "/alerts/action",
                json={
                    "company_id": str(company_id),
                    "alert_code": alert_code,
                    "reference_date": reference_date.isoformat(),
                    "period_start": period_start.isoformat(),
                    "period_end": period_end.isoformat(),
                    "status": status,
                    "note": note or None,
                },
            ),
        )

    def revenue_forecast(
        self,
        company_id: uuid.UUID | str,
        start_date: date,
        end_date: date,
        horizon: int = 3,
    ) -> dict[str, Any]:
        return cast(
            dict[str, Any],
            self._analytics(
                "/predictive/revenue-forecast",
                company_id,
                start_date,
                end_date,
                horizon=horizon,
            ),
        )

    def expense_anomalies(
        self,
        company_id: uuid.UUID | str,
        start_date: date,
        end_date: date,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        return cast(
            list[dict[str, Any]],
            self._analytics(
                "/predictive/expense-anomalies",
                company_id,
                start_date,
                end_date,
                limit=limit,
            ),
        )

    def _analytics(
        self,
        path: str,
        company_id: uuid.UUID | str,
        start_date: date,
        end_date: date,
        **params: Any,
    ) -> Any:
        return self._request(
            "GET",
            path,
            params={
                "company_id": str(company_id),
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                **params,
            },
        )

    def import_transactions(
        self, company_id: uuid.UUID | str, file_name: str, content: bytes
    ) -> dict[str, Any]:
        return cast(
            dict[str, Any],
            self._request(
                "POST",
                "/imports/transactions",
                data={"company_id": str(company_id)},
                files={"file": (file_name, content, "text/csv")},
            ),
        )

    def imports(self, company_id: uuid.UUID | str, page: int = 1) -> dict[str, Any]:
        return cast(
            dict[str, Any],
            self._request(
                "GET",
                "/imports",
                params={"company_id": str(company_id), "page": page, "page_size": 20},
            ),
        )

    def import_issues(self, batch_id: uuid.UUID | str) -> dict[str, Any]:
        return cast(
            dict[str, Any],
            self._request(
                "GET",
                f"/imports/{batch_id}/issues",
                params={"page": 1, "page_size": 100},
            ),
        )
