#!/usr/bin/env python3
"""
Batch convert mjlog XML files to MJAI format using Ruby mjai gem
Handles the conversion by:
1. Gzipping XML files to .mjlog format
2. Converting using mjai gem
3. Optionally validating with Mortal
"""

import os
import subprocess
import sys
from pathlib import Path
import gzip
import shutil
import json
import argparse
from typing import List, Tuple
import tempfile
import concurrent.futures
from datetime import datetime

def gzip_xml_to_mjlog(xml_path: Path, temp_dir: Path) -> Path:
    """Gzip compress XML file to .mjlog format"""
    mjlog_path = temp_dir / f"{xml_path.stem}.mjlog"
    
    with open(xml_path, 'rb') as f_in:
        with gzip.open(mjlog_path, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
    
    return mjlog_path

def convert_mjlog_to_mjai(mjlog_path: Path, output_dir: Path) -> Tuple[bool, str, Path]:
    """Convert .mjlog to .mjson using mjai gem"""
    output_path = output_dir / f"{mjlog_path.stem}.mjson"
    
    # Run mjai convert command
    mjai_cmd = 'C:/Ruby34-x64/bin/mjai.bat' if os.name == 'nt' else 'mjai'
    cmd = [mjai_cmd, 'convert', str(mjlog_path), str(output_path)]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
        
        if result.returncode != 0:
            if "Skipping unsupported file" in result.stderr:
                return False, "Unsupported format", output_path
            else:
                return False, result.stderr[:200], output_path
        
        return True, "Success", output_path
        
    except Exception as e:
        return False, str(e), output_path

def validate_mjai(mjson_path: Path) -> Tuple[bool, str]:
    """Validate MJAI file with Mortal's validate_logs"""
    validator_path = Path("C:/hoge/hoge/Mortal-main/target/debug/validate_logs.exe")
    
    if not validator_path.exists():
        return True, "Validator not found, skipping validation"
    
    try:
        result = subprocess.run(
            [str(validator_path), str(mjson_path)],
            capture_output=True, 
            text=True, 
            encoding='utf-8',
            timeout=10
        )
        
        if result.returncode == 0:
            return True, "Validation passed"
        else:
            # Extract first error for reporting
            errors = result.stderr.split('\n') if result.stderr else []
            first_error = next((e for e in errors if 'fails' in e), "Unknown error")
            return False, first_error[:100]
            
    except subprocess.TimeoutExpired:
        return False, "Validation timeout"
    except Exception as e:
        return False, str(e)

def process_single_file(args: Tuple[Path, Path, Path, bool]) -> dict:
    """Process a single XML file through the entire pipeline"""
    xml_path, temp_dir, output_dir, validate = args
    
    result = {
        'file': xml_path.name,
        'status': 'pending',
        'error': None,
        'validation': None
    }
    
    try:
        # Step 1: Gzip XML to .mjlog
        mjlog_path = gzip_xml_to_mjlog(xml_path, temp_dir)
        
        # Step 2: Convert .mjlog to .mjson
        success, message, mjson_path = convert_mjlog_to_mjai(mjlog_path, output_dir)
        
        if success:
            result['status'] = 'converted'
            
            # Step 3: Optional validation
            if validate and mjson_path.exists():
                valid, validation_msg = validate_mjai(mjson_path)
                result['validation'] = 'passed' if valid else f'failed: {validation_msg}'
        else:
            result['status'] = 'failed'
            result['error'] = message
            
        # Clean up temp file
        mjlog_path.unlink(missing_ok=True)
        
    except Exception as e:
        result['status'] = 'error'
        result['error'] = str(e)
    
    return result

def batch_convert(input_dir: Path, output_dir: Path, validate: bool = False, 
                  max_workers: int = 4, limit: int = None) -> None:
    """Batch convert XML files to MJAI format"""
    
    # Find all XML files
    xml_files = sorted(input_dir.glob("*.xml"))
    
    if not xml_files:
        print(f"No XML files found in {input_dir}")
        return
    
    if limit:
        xml_files = xml_files[:limit]
    
    print(f"Found {len(xml_files)} XML files to convert")
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create temporary directory for .mjlog files
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Prepare arguments for parallel processing
        args_list = [(xml_file, temp_path, output_dir, validate) 
                     for xml_file in xml_files]
        
        # Process files in parallel with progress tracking
        results = []
        start_time = datetime.now()
        
        print(f"\nStarting conversion at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Using {max_workers} parallel workers")
        print("-" * 60)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_file = {executor.submit(process_single_file, args): args[0] 
                            for args in args_list}
            
            completed = 0
            for future in concurrent.futures.as_completed(future_to_file):
                result = future.result()
                results.append(result)
                completed += 1
                
                # Calculate progress and ETA
                elapsed = (datetime.now() - start_time).total_seconds()
                if elapsed > 0:
                    rate = completed / elapsed
                    remaining = len(xml_files) - completed
                    eta_seconds = remaining / rate if rate > 0 else 0
                    
                    # Format time remaining
                    if eta_seconds < 60:
                        eta_str = f"{int(eta_seconds)}s"
                    elif eta_seconds < 3600:
                        eta_str = f"{int(eta_seconds/60)}m {int(eta_seconds%60)}s"
                    else:
                        hours = int(eta_seconds / 3600)
                        mins = int((eta_seconds % 3600) / 60)
                        eta_str = f"{hours}h {mins}m"
                    
                    # Progress bar
                    bar_width = 40
                    progress_pct = completed / len(xml_files)
                    filled = int(bar_width * progress_pct)
                    bar = '=' * filled + '-' * (bar_width - filled)
                    
                    # Status counts
                    successful = sum(1 for r in results if r['status'] == 'converted')
                    failed = sum(1 for r in results if r['status'] in ['failed', 'error'])
                    
                    # Display progress
                    status_line = (f"\r[{bar}] {completed}/{len(xml_files)} "
                                 f"({progress_pct*100:.1f}%) | "
                                 f"OK: {successful} ERR: {failed} | "
                                 f"Speed: {rate:.1f} files/s | "
                                 f"ETA: {eta_str}    ")
                    print(status_line, end='', flush=True)
        
        print()  # New line after progress bar
        elapsed_time = (datetime.now() - start_time).total_seconds()
    
    # Summary statistics
    successful = sum(1 for r in results if r['status'] == 'converted')
    failed = sum(1 for r in results if r['status'] in ['failed', 'error'])
    
    # Format total time
    if elapsed_time < 60:
        time_str = f"{elapsed_time:.1f} seconds"
    elif elapsed_time < 3600:
        time_str = f"{int(elapsed_time/60)}m {int(elapsed_time%60)}s"
    else:
        hours = int(elapsed_time / 3600)
        mins = int((elapsed_time % 3600) / 60)
        secs = int(elapsed_time % 60)
        time_str = f"{hours}h {mins}m {secs}s"
    
    print("\n" + "=" * 60)
    print(f"Conversion Complete at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total Time: {time_str}")
    print(f"Average Speed: {len(xml_files)/elapsed_time:.2f} files/second")
    print(f"Successful: {successful}/{len(xml_files)} ({successful/len(xml_files)*100:.1f}%)")
    print(f"Failed: {failed}/{len(xml_files)} ({failed/len(xml_files)*100:.1f}%)" if failed > 0 else "")
    
    if validate:
        validated = [r for r in results if r['validation'] is not None]
        passed = sum(1 for r in validated if r['validation'] == 'passed')
        print(f"Validation: {passed}/{len(validated)} passed")
    
    # Report errors if any
    errors = [r for r in results if r['status'] in ['failed', 'error']]
    if errors and len(errors) <= 10:
        print("\nErrors:")
        for err in errors[:10]:
            print(f"  {err['file']}: {err['error'][:100]}")
    
    # Save detailed results
    results_file = output_dir / "conversion_results.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nDetailed results saved to: {results_file}")

def main():
    parser = argparse.ArgumentParser(
        description="Batch convert mjlog XML files to MJAI format using Ruby mjai gem"
    )
    parser.add_argument('input_dir', type=Path, help='Directory containing XML files')
    parser.add_argument('output_dir', type=Path, help='Output directory for MJAI files')
    parser.add_argument('-v', '--validate', action='store_true', 
                       help='Validate output with Mortal')
    parser.add_argument('-w', '--workers', type=int, default=4,
                       help='Number of parallel workers (default: 4)')
    parser.add_argument('-l', '--limit', type=int,
                       help='Limit number of files to process')
    
    args = parser.parse_args()
    
    if not args.input_dir.exists():
        print(f"Error: Input directory not found: {args.input_dir}")
        sys.exit(1)
    
    batch_convert(
        args.input_dir, 
        args.output_dir, 
        validate=args.validate,
        max_workers=args.workers,
        limit=args.limit
    )

if __name__ == "__main__":
    main()
