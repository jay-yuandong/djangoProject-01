from django.shortcuts import render
from django.shortcuts import redirect
from . import models,forms
import hashlib,datetime
from django.conf import settings

def send_email(email,code):
    from django.core.mail import EmailMultiAlternatives
    subject='来自jyd测试的注册确认邮件'
    text_content='感谢注册，当您看到此消息时，说明您的邮箱服务器不提供HTML链接功能，请联系管理员'
    html_content="""
                    >感谢注册<a href="http://{}/confirm/?code={}" target=blank>www.baidu.com</a>，\
                    吧啦吧啦</p>
                    <p>请点击站点链接完成注册确认！</p>
                    <p>此链接有效期为{}天！</p>
                    """.format('127.0.0.1:8000',code,settings.CONFIRM_DAYS)
    msg=EmailMultiAlternatives(subject,text_content,settings.EMAIL_HOST_USER,[email])
    msg.attach_alternative(html_content,'text/html')
    msg.send()

def make_confirm_string(user):
    now=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    code=hash_code(user.name,now)
    models.ConfirmString.objects.create(code=code,user=user)
    return code

def hash_code(s,salt='djangoProject'):
    h=hashlib.sha256()
    s+=salt
    h.update(s.encode())
    return h.hexdigest()

# Create your views here.

def index(request):
    #如果未登录，进不了index页
    if not request.session.get('is_login',None):
        return redirect('/login/')
    return render(request,'login/index.html')

def login(request):
    #不允许重复登录
    if request.session.get('is_login',None):
        return redirect('/index/')
    if request.method=='POST':
        login_form=forms.UserForm(request.POST)
        message="请检查填写的内容"

        if login_form.is_valid():
            #从表单对象的cleaned_data数据字典获取数据
            username=login_form.cleaned_data.get('username')
            password=login_form.cleaned_data.get('password')
            try:
                user=models.User.objects.get(name=username)
            except:
                message='用户不存在！'
                return render(request,'login/login.html',locals())

            if not user.has_confirmed:
                message='该用户还未经邮件确认！'
                return render(request,'login/login.html',locals())

            if user.password==hash_code(password):
                request.session['is_login']=True
                request.session['user_id']=user.id
                request.session['user_name']=user.name
                return redirect('/index/')
            else:
                message='密码不正确！'
                return render(request,'login/login.html',locals())
        else:
            return render(request,'login/login.html',locals())

    #非post方法，返回空表单，用户继续注册
    login_form=forms.UserForm()
    return render(request,'login/login.html',locals())




def register(request):
    if request.session.get('is_login',None):
        return redirect('/index/')

    if request.method=='POST':
        register_form=forms.RegisterForm(request.POST)
        message="请检查填写的内容！"
        if register_form.is_valid():
            username=register_form.cleaned_data.get('username')
            password1=register_form.cleaned_data.get('password1')
            password2=register_form.cleaned_data.get('password2')
            eamil=register_form.cleaned_data.get('email')
            sex=register_form.cleaned_data.get('sex')

            #首先校验2次输入的密码
            if password2!=password1:
                message='两次输入的密码不同！'
                return render(request,'login/register.html',locals())

            else:
                #校验注册的用户名是否已存在
                same_name_user=models.User.objects.filter(name=username)
                if same_name_user:
                    message='用户名已存在'
                    return render(request,'login/register.html',locals())
                #校验邮箱是否已存在
                same_email_user=models.User.objects.filter(email=eamil)
                if same_email_user:
                    message='该邮箱已经被注册了！'
                    return render(request,'login/register.html',locals())
                #两次密码一致，用户名不存在，邮箱未被注册，创建一个用户实例models.User()，将信息保存到数据库
                new_user=models.User()
                new_user.name=username
                new_user.password=hash_code(password1)
                new_user.email=eamil
                new_user.sex=sex
                new_user.save()

                code=make_confirm_string(new_user)
                send_email(eamil,code)
                message='请前往邮箱进行确认'
                return render(request,'login/confirm.html',locals())
        else:
            return render(request,'login/register.html',locals())
    register_form=forms.RegisterForm()
    return render(request,'login/register.html',locals())


def logout(request):
    #如果本没有登录，就没有登出
    if not request.session.get('is_login',None):
        return redirect('/login/')

    #将session中的所有内容全部清空
    request.session.flush()

    #重定向到login
    return redirect('/login/')

#用户注册确认
def user_confirm(request):
    #从用户的点击确认的链接获取code
    code=request.GET.get('code',None)
    message=''
    try:
        confirm=models.ConfirmString.objects.get(code=code)
    except:
        message='无效的确认请求'
        return render(request,'login/confirm.html',locals())

    c_time=confirm.c_time
    now=datetime.datetime.now()
    #链接过期
    if now>c_time+datetime.timedelta(settings.CONFIRM_DAYS):
        #删除该条用户信息
        confirm.user.delete()
        message='您的邮件已过期，请重新注册！'
        return render(request,'login/register.html',locals())
    else:
        #没过期，将该用户的has_confirmed字段修改为true
        confirm.user.has_confirmed=True
        #保存用户，但是删除注册码
        confirm.user.save()
        confirm.delete()
        message='感谢确认，请使用账户登录'
        return render(request,'login/confirm.html',locals())
