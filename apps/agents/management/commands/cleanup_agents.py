"""
Management command to cleanup old agent executions and optimize database.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from apps.agents.models import AgentExecution, Agent
from django.db.models import Count, Avg


class Command(BaseCommand):
    help = 'Cleanup old agent executions and optimize database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Number of days to keep executions (default: 30)',
        )
        parser.add_argument(
            '--update-stats',
            action='store_true',
            help='Update agent statistics after cleanup',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )

    def handle(self, *args, **options):
        days = options['days']
        update_stats = options['update_stats']
        dry_run = options['dry_run']
        
        threshold_date = timezone.now() - timedelta(days=days)
        
        self.stdout.write(f'\nSearching for executions older than {days} days...')
        self.stdout.write(f'Threshold date: {threshold_date.strftime("%Y-%m-%d %H:%M:%S")}')
        
        # Find old executions
        old_executions = AgentExecution.objects.filter(
            created_at__lt=threshold_date,
            status__in=['success', 'failed', 'cancelled']
        )
        
        count = old_executions.count()
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS('\n✓ No old executions found to delete'))
            return
        
        # Show statistics
        self.stdout.write(f'\nFound {count} executions to delete:')
        
        status_counts = old_executions.values('status').annotate(
            count=Count('id')
        ).order_by('-count')
        
        for item in status_counts:
            self.stdout.write(f"  - {item['status']}: {item['count']}")
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('\n⚠ DRY RUN MODE: No deletions will be performed')
            )
            return
        
        # Confirm deletion
        confirm = input(f'\nDo you want to delete these {count} executions? (yes/no): ')
        
        if confirm.lower() != 'yes':
            self.stdout.write(self.style.WARNING('\nDeletion cancelled'))
            return
        
        # Delete executions
        self.stdout.write('\nDeleting executions...')
        deleted_count, _ = old_executions.delete()
        
        self.stdout.write(
            self.style.SUCCESS(f'✓ Deleted {deleted_count} old executions')
        )
        
        # Update statistics if requested
        if update_stats:
            self.stdout.write('\nUpdating agent statistics...')
            
            agents = Agent.objects.all()
            updated_count = 0
            
            for agent in agents:
                executions = agent.executions.all()
                total = executions.count()
                success = executions.filter(status='success').count()
                failed = executions.filter(status='failed').count()
                
                if (total != agent.execution_count or 
                    success != agent.success_count or 
                    failed != agent.failure_count):
                    
                    agent.execution_count = total
                    agent.success_count = success
                    agent.failure_count = failed
                    agent.save()
                    updated_count += 1
            
            self.stdout.write(
                self.style.SUCCESS(f'✓ Updated statistics for {updated_count} agents')
            )
        
        self.stdout.write(
            self.style.SUCCESS('\n✓ Cleanup completed successfully!')
        )
