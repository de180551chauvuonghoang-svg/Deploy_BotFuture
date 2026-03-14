import pandas as pd
import numpy as np

def analyze():
    try:
        df = pd.read_csv('backtest_trades_hardstop.csv')
        # Ensure time is datetime
        df['time'] = pd.to_datetime(df['time'])
        
        # Losses only
        losses = df[df['pnl'] < 0].copy()
        
        total_loss_val = abs(losses['pnl'].sum())
        total_pnl_val = df['pnl'].sum()
        
        print(f"Total Losing Trades: {len(losses)}")
        print(f"Total Loss Amount: -{total_loss_val:.2f} USDT")
        
        print("\n--- 1. LOSS BY REASON ---")
        reason_counts = losses['reason'].value_counts()
        reason_pnl = losses.groupby('reason')['pnl'].sum()
        for reason in reason_counts.index:
            print(f"- {reason}: {reason_counts[reason]} trades | Total: {reason_pnl[reason]:.2f} USDT")

        print("\n--- 2. TOP 5 LOSING SYMBOLS (BY TOTAL PNL) ---")
        symbol_loss = losses.groupby('symbol')['pnl'].sum().sort_values().head(5)
        for sym, val in symbol_loss.items():
            print(f"- {sym}: {val:.2f} USDT")

        print("\n--- 3. PATTERN ANALYSIS ---")
        # Check for "REVERSAL" vs "STOP_LOSS"
        reversals = losses[losses['reason'].str.contains('REVERSAL', na=False)]
        hard_sl = losses[losses['reason'] == 'STOP_LOSS']
        
        print(f"- Signal Reversals: {len(reversals)} trades (Market flipped against us)")
        print(f"- Hard Stop Loss Hits: {len(hard_sl)} trades (Hit SL before any reversal/TP)")
        
        # Duration analysis for losses
        # This is tricky because the CSV records separate rows for partials. 
        # But we can look at the average time between entry and a loss record.
        # Actually, let's just find trades where pnl < 0 and analyze their timing.
        
    except Exception as e:
        print(f"Error analyzing: {e}")

if __name__ == "__main__":
    analyze()
