from training_sync.weightxreps.auth import (
    TokenSet,
    build_authorization_url,
    exchange_code_for_tokens,
    generate_pkce_pair,
    load_tokens,
    refresh_access_token,
    save_tokens,
)


def test_generate_pkce_pair_uses_short_verifier_and_s256_challenge():
    pair = generate_pkce_pair()

    assert 43 <= len(pair.code_verifier) <= 64
    assert pair.code_challenge
    assert pair.code_challenge_method == "S256"
    assert pair.code_challenge != pair.code_verifier


def test_build_authorization_url_contains_weightxreps_params():
    url = build_authorization_url(
        client_id="training-sync",
        redirect_uri="http://127.0.0.1:8765/callback",
        scope="jread,jwrite",
        state="state-123",
        code_challenge="challenge-123",
    )

    assert url.startswith("https://weightxreps.net/api/auth?")
    assert "client_id=training-sync" in url
    assert "redirect_uri=http%3A%2F%2F127.0.0.1%3A8765%2Fcallback" in url
    assert "scope=jread%2Cjwrite" in url
    assert "code_challenge=challenge-123" in url
    assert "code_challenge_method=S256" in url


def test_token_store_round_trips_json(tmp_path):
    path = tmp_path / "weightxreps-token.json"
    tokens = TokenSet(
        access_token="access",
        refresh_token="refresh",
        expires_in=3600,
        token_type="Bearer",
    )

    save_tokens(path, tokens)

    assert load_tokens(path) == tokens


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self):
        self.calls = []

    def post(self, url, data):
        self.calls.append((url, data))
        return FakeResponse(
            {
                "access_token": "access",
                "refresh_token": "refresh",
                "expires_in": 3600,
                "token_type": "Bearer",
            }
        )


def test_exchange_code_for_tokens_posts_pkce_form():
    session = FakeSession()

    tokens = exchange_code_for_tokens(
        client_id="training-sync",
        redirect_uri="http://127.0.0.1:8765/callback",
        code="code-123",
        code_verifier="verifier-123",
        session=session,
    )

    assert tokens.access_token == "access"
    assert session.calls == [
        (
            "https://weightxreps.net/api/auth/token",
            {
                "grant_type": "authorization_code",
                "client_id": "training-sync",
                "redirect_uri": "http://127.0.0.1:8765/callback",
                "code": "code-123",
                "code_verifier": "verifier-123",
            },
        )
    ]


def test_refresh_access_token_posts_refresh_token_form():
    session = FakeSession()

    tokens = refresh_access_token(
        client_id="training-sync",
        refresh_token="refresh-123",
        session=session,
    )

    assert tokens.access_token == "access"
    assert tokens.refresh_token == "refresh"
    assert session.calls == [
        (
            "https://weightxreps.net/api/auth/token",
            {
                "grant_type": "refresh_token",
                "client_id": "training-sync",
                "refresh_token": "refresh-123",
            },
        )
    ]
