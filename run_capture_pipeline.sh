#!/bin/bash
# Abyssal Siege 캡처 전체 파이프라인
# Unity 컴파일 완료 감지 → 트리거 생성 → 완료 대기 → Python 실행

ASSETS_DIR="C:/Users/wonil.cho.SUPERCAT/Desktop/Abyssal Siege/AS_Assets"
DLL="C:/Users/wonil.cho.SUPERCAT/icecat/grandcross-client/Library/ScriptAssemblies/Assembly-CSharp.dll"
VALK_TRIGGER="$ASSETS_DIR/.valk_trigger"
ALL_DONE="$ASSETS_DIR/.all_done"
ABYSSAL_DIR="C:/Users/wonil.cho.SUPERCAT/Desktop/Abyssal Siege"

INITIAL_TS=1776760723
echo "[Pipeline] Unity 컴파일 완료 대기 중..."

# 1. Unity 컴파일 완료 대기 (DLL 타임스탬프 변경 감지)
for i in $(seq 1 120); do
    if [ -f "$DLL" ]; then
        CURRENT_TS=$(stat -c "%Y" "$DLL" 2>/dev/null || echo "0")
        if [ "$CURRENT_TS" -gt "$INITIAL_TS" ]; then
            echo "[Pipeline] Unity 컴파일 완료 (${i}초)"
            break
        fi
    fi
    sleep 2
    if [ "$i" -eq 120 ]; then
        echo "[Pipeline] 컴파일 대기 타임아웃 — 트리거 그냥 생성"
    fi
done

# 추가 2초 대기 (Unity 초기화 완료)
sleep 2

# 2. 발키리 캡처 트리거 생성
echo "[Pipeline] 발키리 캡처 트리거 생성..."
echo "trigger" > "$VALK_TRIGGER"

# 3. 전체 완료 대기 (최대 30분)
echo "[Pipeline] 캡처 완료 대기 중... (최대 30분)"
for i in $(seq 1 360); do
    if [ -f "$ALL_DONE" ]; then
        echo "[Pipeline] ✅ 모든 캡처 완료 (${i}초)"
        rm -f "$ALL_DONE"
        break
    fi
    sleep 5
    if [ "$i" -eq 360 ]; then
        echo "[Pipeline] ⚠️ 타임아웃 — Python 실행 시도"
    fi
done

# 4. Python 스크립트 실행
echo "[Pipeline] Python 스프라이트 시트 생성 중..."
cd "$ABYSSAL_DIR"

python make_valk_sprites.py
if [ $? -eq 0 ]; then
    echo "[Pipeline] ✅ make_valk_sprites.py 완료"
else
    echo "[Pipeline] ❌ make_valk_sprites.py 실패"
fi

python make_fx_sprites.py
if [ $? -eq 0 ]; then
    echo "[Pipeline] ✅ make_fx_sprites.py 완료"
else
    echo "[Pipeline] ❌ make_fx_sprites.py 실패"
fi

echo "[Pipeline] 🎉 전체 파이프라인 완료!"
