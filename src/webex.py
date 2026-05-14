import os
import pandas as pd
import logging
from datetime import datetime, timedelta
from wxc_sdk import WebexSimpleApi
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, MofNCompleteColumn, TimeElapsedColumn

logger = logging.getLogger("webex")

class WebexAuditClient:
    def __init__(self):
        # WebexSimpleApi handles retry_429 and tokens automatically via env
        self.api = WebexSimpleApi(retry_429=True)

    def get_time_windows(self, start_dt: datetime, end_dt: datetime, interval_hours=12):
        """Chunks the year into manageable segments."""
        windows = []
        current_start = start_dt
        while current_start < end_dt:
            current_end = current_start + timedelta(hours=interval_hours)
            if current_end > end_dt:
                current_end = end_dt
            windows.append((current_start, current_end))
            current_start = current_end
        return windows

    def fetch_recordings_for_audit(self, start_dt: datetime, end_dt: datetime, output_path):
        """
        The core engine that performs the sync for the audit year.
        Returns a list of dictionaries for the reconciler.
        """
        
        windows = self.get_time_windows(start_dt, end_dt)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
            transient=False
        ) as progress:
            
            overall_task = progress.add_task("[yellow]Scanning Webex History", total=len(windows))
            record_task = progress.add_task("[cyan]Metadata Retrieved", total=None)

            for s_win, e_win in windows:
                s_iso = s_win.strftime('%Y-%m-%dT%H:%M:%SZ')
                e_iso = e_win.strftime('%Y-%m-%dT%H:%M:%SZ')
                
                progress.update(overall_task, description=f"[yellow]Window: {s_win.strftime('%m/%d %H:%M')}")
                record_task = progress.add_task("[cyan]Records Written", total=None)

                try:
                    # Using converged recordings for the compliance officer view
                    recordings_gen = self.api.converged_recordings.list_for_admin_or_compliance_officer(
                        from_=s_iso, to_=e_iso
                    )
                    
                    batch = []
                    for rec in recordings_gen:
                        # CRITICAL: This is the ID we match against Calabrio's callId
                        session_id = rec.service_data.call_session_id if rec.service_data else None
                        
                        if session_id:
                            batch.append({
                                'sessionId': session_id,
                                'startTime': rec.time_recorded,
                                'ownerEmail': rec.owner_email,
                                'duration': rec.duration_seconds,
                                'status': str(rec.status.value) if hasattr(rec.status, 'value') else str(rec.status)
                            })
                        
                        progress.advance(record_task)
                    
                    if batch:
                        df = pd.DataFrame(batch)
                        # Append mode ('a') with header only on the first write
                        df.to_csv(output_path, mode='a', index=False, header=not os.path.exists(output_path))
                
                except Exception as e:
                    logger.error(f"Error fetching Webex window {s_iso}: {e}")

                progress.advance(overall_task)

        return progress.tasks[1].completed