# 🚨 Render Database Troubleshooting Guide

This guide will help you resolve database connection issues and admin access problems on Render.

## 🔍 **Immediate Actions to Take**

### **Step 1: Check Your Render Dashboard**

1. Go to your Render dashboard (render.com)
2. Click on your `nola-docs` service
3. Check the **Environment** tab:
   - Verify `DATABASE_URL` is set (should show as connected)
   - Verify `SECRET_KEY` is set
   - Verify `FLASK_ENV` is set to `production`

### **Step 2: Check Database Status**

1. In your Render dashboard, go to the **Databases** section
2. Look for `nola-docs-db`
3. Status should be "Available" (green)
4. Note the connection info

### **Step 3: Check Recent Deployment Logs**

1. In your service dashboard, click **Logs**
2. Look for recent deployment messages
3. Check for any database connection errors
4. Look for migration success/failure messages

## 🛠️ **Fix Database Issues**

### **Option A: Use the Shell to Run Diagnostics**

1. In your Render service dashboard, click **Shell**
2. Run the diagnostic script:
   ```bash
   python debug_db.py
   ```
3. Follow the menu options:
   - Option 1: List all users (see if any exist)
   - Option 2: Create default admin
   - Option 4: Run migrations if needed

### **Option B: Manual Database Reset (If needed)**

If your database seems corrupted or empty:

1. In Render dashboard, go to your database
2. **ONLY IF ABSOLUTELY NECESSARY**: Delete and recreate the database
3. Redeploy your service (this will run migrations automatically)

### **Option C: Force Redeploy with New Scripts**

1. Commit the new files I created (`debug_db.py`, `render_deploy.py`, updated `render.yaml`)
2. Push to your Git repository
3. Render will automatically redeploy
4. The new deployment should create an admin user automatically

## 🔐 **Admin Access Solutions**

### **Default Admin Credentials**
After running the setup scripts, try logging in with:
- **Email**: `admin@nola.edu`
- **Username**: `admin`
- **Password**: `admin123`

⚠️ **CHANGE THIS PASSWORD IMMEDIATELY** after logging in!

### **If Default Admin Doesn't Work**

1. Use the Render Shell:
   ```bash
   python debug_db.py
   ```
2. Select option 3 to create a custom admin
3. Or select option 1 to see if users exist

## 🚨 **Common Issues & Solutions**

### **Issue: "Database resets on every deployment"**

**Cause**: You might be using a development database or have migration issues.

**Solution**:
1. Ensure you're using the PostgreSQL database defined in `render.yaml`
2. Check that migrations are running successfully
3. Verify your `DATABASE_URL` points to the persistent database

### **Issue: "Can't connect to database"**

**Solutions**:
1. Check Render database status in dashboard
2. Verify environment variables are set correctly
3. Try restarting your service
4. Check recent deployment logs for errors

### **Issue: "Admin user doesn't exist"**

**Solutions**:
1. Run `python debug_db.py` in Render Shell
2. Create admin using option 2 or 3
3. Or redeploy with the new automated setup

### **Issue: "Password doesn't work"**

**Solutions**:
1. Use the diagnostic script to reset password
2. Ensure you're using the correct email/username
3. Try both email and username for login

## 📊 **Verification Steps**

After fixing, verify everything works:

1. **Database Connection**: Run diagnostic script, option 5
2. **Admin Access**: Try logging in with admin credentials
3. **User Creation**: As admin, try creating a new user
4. **Document Generation**: Try creating a vocabulary worksheet

## 🔄 **Prevention for Future Deployments**

1. **Always use the persistent PostgreSQL database** (not SQLite)
2. **Ensure migrations run in the build command** (already in `render.yaml`)
3. **Keep the automated setup scripts** (`render_deploy.py`)
4. **Don't delete the database** unless absolutely necessary

## 📞 **If You're Still Stuck**

1. **Check Render Status Page**: status.render.com
2. **Review Render Documentation**: render.com/docs/databases
3. **Send me the error logs** from your Render dashboard

## 🚀 **Quick Recovery Commands**

If you need immediate access, run these in the Render Shell:

```bash
# Check everything
python debug_db.py

# Or just create admin quickly
python -c "
from app import app
from models import db, User
with app.app_context():
    admin = User(email='admin@nola.edu', username='admin', first_name='Admin', last_name='User', is_admin=True, is_active=True)
    admin.set_password('admin123')
    db.session.add(admin)
    db.session.commit()
    print('Admin created: admin@nola.edu / admin123')
"
```

---

## 📋 **Summary Checklist**

- [ ] Database status is "Available" in Render dashboard
- [ ] All environment variables are set
- [ ] Recent deployment completed successfully
- [ ] Admin user exists and password works
- [ ] Can create documents successfully
- [ ] Changed default password

Remember: The new scripts will automatically handle most of these issues on future deployments! 