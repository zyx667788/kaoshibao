module.exports = {
  apps: [
    {
      name: 'kaoshibao',
      script: 'venv/bin/python',
      args: 'app.py',
      cwd: '/home/user/kaoshibao',  // 修改为实际部署路径
      instances: 1,
      exec_mode: 'fork',
      watch: false,
      max_memory_restart: '500M',
      env: {
        NODE_ENV: 'production',
        PORT: 5678,
      },
      error_file: '/home/user/kaoshibao/logs/err.log',
      out_file: '/home/user/kaoshibao/logs/out.log',
      log_file: '/home/user/kaoshibao/logs/combined.log',
      time: true,
      merge_logs: true,
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      restart_delay: 3000,
      max_restarts: 10,
      min_uptime: '10s',
      kill_timeout: 5000,
      listen_timeout: 8000,
    },
  ],
};