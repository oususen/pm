#!/bin/bash
# 本番環境用SSL証明書生成スクリプト
# 使用方法: ./generate-prod-cert.sh

CERT_DIR="$(dirname "$0")"
cd "$CERT_DIR"

# CA証明書を生成（既存があれば再利用可能）
if [ ! -f "pm-ca.key" ]; then
    echo "=== CA秘密鍵を生成 ==="
    openssl genrsa -out pm-ca.key 2048

    echo "=== CA証明書を生成 ==="
    openssl req -x509 -new -nodes -key pm-ca.key -sha256 -days 3650 \
        -out pm-ca.crt \
        -subj "//CN=PM Local CA\O=PM\C=JP"
fi

# サーバー証明書用の設定ファイル
cat > pm-prod.ext << EOF
authorityKeyIdentifier=keyid,issuer
basicConstraints=CA:FALSE
keyUsage = digitalSignature, nonRepudiation, keyEncipherment, dataEncipherment
subjectAltName = @alt_names

[alt_names]
DNS.1 = localhost
DNS.2 = pm-frontend
DNS.3 = pm-backend
IP.1 = 127.0.0.1
IP.2 = 10.0.1.232
IP.3 = 192.168.0.7
IP.4 = 192.168.0.11
IP.5 = 10.0.1.194
EOF

echo "=== サーバー秘密鍵を生成 ==="
openssl genrsa -out pm-prod.key 2048

echo "=== CSRを生成 ==="
openssl req -new -key pm-prod.key -out pm-prod.csr \
    -subj "//CN=pm-prod\O=PM\C=JP"

echo "=== サーバー証明書を生成 ==="
openssl x509 -req -in pm-prod.csr \
    -CA pm-ca.crt -CAkey pm-ca.key -CAcreateserial \
    -out pm-prod.crt -days 825 -sha256 \
    -extfile pm-prod.ext

echo "=== 証明書の確認 ==="
openssl x509 -in pm-prod.crt -noout -text | grep -A1 "Subject Alternative Name"

echo ""
echo "=== 完了 ==="
echo "生成されたファイル:"
echo "  - pm-ca.crt     : CA証明書（ブラウザにインポート）"
echo "  - pm-prod.crt   : サーバー証明書"
echo "  - pm-prod.key   : サーバー秘密鍵"
echo ""
echo "ブラウザでの警告を回避するには、pm-ca.crt を"
echo "「信頼されたルート証明機関」としてインポートしてください。"
