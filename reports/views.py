from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.core.paginator import Paginator
from orders.models import Order, OrderItem
from cashier.models import Payment
from restaurant.models import MainCategory, SubCategory
from accounts.models import get_owner_filter
from django.db.models import Sum, Count
from datetime import datetime, timedelta
from django.utils import timezone
import csv

# PDF export libraries
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from io import BytesIO

@login_required
def dashboard(request):
    """Simple sales reports dashboard"""
    
    # Get owner filter for multi-tenant support
    owner = get_owner_filter(request.user)
    
    # Get filter parameters
    payment_status = request.GET.get('payment_status', 'all')
    period = request.GET.get('period', 'all')
    category_id = request.GET.get('category_id', 'all')
    subcategory_id = request.GET.get('subcategory_id', 'all')
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    
    # Base queryset - filter by owner through table_info
    orders = Order.objects.filter(table_info__owner=owner)
    
    # Apply period filter
    today = timezone.now().date()
    if period == 'today':
        orders = orders.filter(created_at__date=today)
    elif period == 'weekly':
        week_start = today - timedelta(days=today.weekday())
        orders = orders.filter(created_at__date__gte=week_start)
    elif period == 'monthly':
        month_start = today.replace(day=1)
        orders = orders.filter(created_at__date__gte=month_start)
    elif period == 'yearly':
        year_start = today.replace(month=1, day=1)
        orders = orders.filter(created_at__date__gte=year_start)
    # 'all' period means no date filter - show all orders
    
    # Apply category filter
    if category_id != 'all':
        orders = orders.filter(order_items__product__main_category_id=category_id).distinct()
    
    # Apply subcategory filter
    if subcategory_id != 'all':
        orders = orders.filter(order_items__product__sub_category_id=subcategory_id).distinct()
    
    # Apply payment status filter
    if payment_status == 'paid':
        orders = orders.filter(payment_status='paid')
    elif payment_status == 'unpaid':
        orders = orders.filter(payment_status='unpaid')
    elif payment_status == 'partial':
        orders = orders.filter(payment_status='partial')
    
    # Apply date filters (these override period if specified)
    if from_date:
        orders = orders.filter(created_at__date__gte=from_date)
    if to_date:
        orders = orders.filter(created_at__date__lte=to_date)
    
    # Calculate summary data
    total_orders = orders.count()
    total_revenue = orders.aggregate(total=Sum('total_amount'))['total'] or 0
    total_items = OrderItem.objects.filter(order__in=orders).aggregate(total=Sum('quantity'))['total'] or 0
    avg_order_value = (total_revenue / total_orders) if total_orders > 0 else 0
    
    # Get orders for table with pagination
    orders_list = orders.order_by('-created_at')
    
    # Pagination
    page_number = request.GET.get('page', 1)
    paginator = Paginator(orders_list, 10)  # Show 10 orders per page
    page_obj = paginator.get_page(page_number)
    
    # Get categories and subcategories for the current owner
    categories = MainCategory.objects.filter(owner=owner)
    subcategories = SubCategory.objects.filter(main_category__owner=owner)
    
    # Filter subcategories by selected category if applicable
    if category_id != 'all':
        subcategories = subcategories.filter(main_category_id=category_id)
    
    context = {
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'total_items': total_items,
        'avg_order_value': avg_order_value,
        'page_obj': page_obj,
        'orders': page_obj,
        'payment_status': payment_status,
        'categories': categories,
        'subcategories': subcategories,
        'selected_category': category_id,
        'selected_subcategory': subcategory_id,
    }
    
    return render(request, 'reports/dashboard.html', context)

@login_required
def export_csv(request):
    """Export filtered data to CSV"""
    
    # Get owner filter for multi-tenant support
    owner = get_owner_filter(request.user)
    
    # Get same filters as dashboard
    payment_status = request.GET.get('payment_status', 'all')
    period = request.GET.get('period', 'all')
    category_id = request.GET.get('category_id', 'all')
    subcategory_id = request.GET.get('subcategory_id', 'all')
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    
    # Base queryset - filter by owner through table_info
    orders = Order.objects.filter(table_info__owner=owner)
    
    # Apply period filter
    today = timezone.now().date()
    if period == 'today':
        orders = orders.filter(created_at__date=today)
    elif period == 'weekly':
        week_start = today - timedelta(days=today.weekday())
        orders = orders.filter(created_at__date__gte=week_start)
    elif period == 'monthly':
        month_start = today.replace(day=1)
        orders = orders.filter(created_at__date__gte=month_start)
    elif period == 'yearly':
        year_start = today.replace(month=1, day=1)
        orders = orders.filter(created_at__date__gte=year_start)
    # 'all' period means no date filter - show all orders
    
    # Apply category filter
    if category_id != 'all':
        orders = orders.filter(order_items__product__main_category_id=category_id).distinct()
    
    # Apply subcategory filter
    if subcategory_id != 'all':
        orders = orders.filter(order_items__product__sub_category_id=subcategory_id).distinct()
    
    # Apply payment status filter
    if payment_status == 'paid':
        orders = orders.filter(payment_status='paid')
    elif payment_status == 'unpaid':
        orders = orders.filter(payment_status='unpaid')
    elif payment_status == 'partial':
        orders = orders.filter(payment_status='partial')
    
    # Apply date filters (these override period if specified)
    if from_date:
        orders = orders.filter(created_at__date__gte=from_date)
    if to_date:
        orders = orders.filter(created_at__date__lte=to_date)
    
    # Calculate summary data for the export
    total_orders = orders.count()
    total_revenue = orders.aggregate(total=Sum('total_amount'))['total'] or 0
    total_items = OrderItem.objects.filter(order__in=orders).aggregate(total=Sum('quantity'))['total'] or 0
    avg_order_value = (total_revenue / total_orders) if total_orders > 0 else 0
    
    # Determine the period description for the report
    if from_date and to_date:
        period_desc = f"Custom Period: {from_date} to {to_date}"
    elif from_date:
        period_desc = f"From: {from_date}"
    elif to_date:
        period_desc = f"Until: {to_date}"
    elif period == 'today':
        period_desc = f"Today: {today}"
    elif period == 'weekly':
        week_start = today - timedelta(days=today.weekday())
        period_desc = f"This Week: {week_start} to {today}"
    elif period == 'monthly':
        month_start = today.replace(day=1)
        period_desc = f"This Month: {month_start} to {today}"
    elif period == 'yearly':
        year_start = today.replace(month=1, day=1)
        period_desc = f"This Year: {year_start} to {today}"
    else:
        period_desc = "All Time"
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="sales_report_{payment_status}_{period}_{datetime.now().strftime("%Y%m%d")}.csv"'
    
    writer = csv.writer(response)
    
    # Write summary header
    writer.writerow(['SALES REPORT SUMMARY'])
    writer.writerow(['Generated on:', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
    writer.writerow(['Period:', period_desc])
    writer.writerow(['Payment Status Filter:', payment_status.title()])
    if category_id != 'all':
        try:
            category_name = MainCategory.objects.get(id=category_id, owner=owner).name
            writer.writerow(['Category Filter:', category_name])
        except:
            writer.writerow(['Category Filter:', f'Category ID {category_id}'])
    if subcategory_id != 'all':
        try:
            subcategory_name = SubCategory.objects.get(id=subcategory_id, main_category__owner=owner).name
            writer.writerow(['Sub Category Filter:', subcategory_name])
        except:
            writer.writerow(['Sub Category Filter:', f'Sub Category ID {subcategory_id}'])
    writer.writerow([])  # Empty row
    
    # Write summary statistics
    writer.writerow(['SUMMARY STATISTICS'])
    writer.writerow(['Total Revenue:', f'${total_revenue:,.2f}'])
    writer.writerow(['Total Orders:', f'{total_orders:,}'])
    writer.writerow(['Items Sold:', f'{total_items:,}'])
    writer.writerow(['Average Order Value:', f'${avg_order_value:,.2f}'])
    writer.writerow([])  # Empty row
    writer.writerow([])  # Empty row
    
    # Write detailed data header
    writer.writerow(['DETAILED SALES DATA'])
    writer.writerow(['Order ID', 'Customer', 'Date', 'Table', 'Items', 'Categories', 'Sub Categories', 'Total Amount', 'Payment Status', 'Order Status', 'Cashier'])
    
    for order in orders.order_by('-created_at'):
        items_list = ', '.join([f"{item.product.name} x{item.quantity}" for item in order.order_items.all()])
        categories_list = ', '.join([item.product.main_category.name for item in order.order_items.all()])
        subcategories_list = ', '.join([item.product.sub_category.name if item.product.sub_category else '-' for item in order.order_items.all()])
        table_number = order.table_info.tbl_no if order.table_info else '-'
        customer_name = f"{order.ordered_by.first_name} {order.ordered_by.last_name}" if order.ordered_by else 'Walk-in Customer'
        cashier_name = f"{order.confirmed_by.first_name} {order.confirmed_by.last_name}" if order.confirmed_by else f"{order.ordered_by.first_name} {order.ordered_by.last_name} (Self)" if order.ordered_by else 'System'
        
        writer.writerow([
            f"ORD-{order.id:08d}",
            customer_name,
            order.created_at.strftime('%Y-%m-%d %H:%M'),
            table_number,
            items_list,
            categories_list,
            subcategories_list,
            order.total_amount,
            order.payment_status,
            order.status,
            cashier_name
        ])
    
    return response

@login_required
def export_pdf(request):
    """Export filtered data to PDF"""
    
    # Get owner filter for multi-tenant support
    owner = get_owner_filter(request.user)
    
    # Get same filters as dashboard
    payment_status = request.GET.get('payment_status', 'all')
    period = request.GET.get('period', 'all')
    category_id = request.GET.get('category_id', 'all')
    subcategory_id = request.GET.get('subcategory_id', 'all')
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    
    # Base queryset - filter by owner through table_info
    orders = Order.objects.filter(table_info__owner=owner)
    
    # Apply period filter
    today = timezone.now().date()
    if period == 'today':
        orders = orders.filter(created_at__date=today)
    elif period == 'weekly':
        week_start = today - timedelta(days=today.weekday())
        orders = orders.filter(created_at__date__gte=week_start)
    elif period == 'monthly':
        month_start = today.replace(day=1)
        orders = orders.filter(created_at__date__gte=month_start)
    elif period == 'yearly':
        year_start = today.replace(month=1, day=1)
        orders = orders.filter(created_at__date__gte=year_start)
    # 'all' period means no date filter - show all orders
    
    # Apply category filter
    if category_id != 'all':
        orders = orders.filter(order_items__product__main_category_id=category_id).distinct()
    
    # Apply subcategory filter
    if subcategory_id != 'all':
        orders = orders.filter(order_items__product__sub_category_id=subcategory_id).distinct()
    
    # Apply payment status filter
    if payment_status == 'paid':
        orders = orders.filter(payment_status='paid')
    elif payment_status == 'unpaid':
        orders = orders.filter(payment_status='unpaid')
    elif payment_status == 'partial':
        orders = orders.filter(payment_status='partial')
    
    # Apply date filters (these override period if specified)
    if from_date:
        orders = orders.filter(created_at__date__gte=from_date)
    if to_date:
        orders = orders.filter(created_at__date__lte=to_date)
    
    # Calculate summary data for the export
    total_orders = orders.count()
    total_revenue = orders.aggregate(total=Sum('total_amount'))['total'] or 0
    total_items = OrderItem.objects.filter(order__in=orders).aggregate(total=Sum('quantity'))['total'] or 0
    avg_order_value = (total_revenue / total_orders) if total_orders > 0 else 0
    
    # Determine the period description for the report
    if from_date and to_date:
        period_desc = f"Custom Period: {from_date} to {to_date}"
    elif from_date:
        period_desc = f"From: {from_date}"
    elif to_date:
        period_desc = f"Until: {to_date}"
    elif period == 'today':
        period_desc = f"Today: {today}"
    elif period == 'weekly':
        week_start = today - timedelta(days=today.weekday())
        period_desc = f"This Week: {week_start} to {today}"
    elif period == 'monthly':
        month_start = today.replace(day=1)
        period_desc = f"This Month: {month_start} to {today}"
    elif period == 'yearly':
        year_start = today.replace(month=1, day=1)
        period_desc = f"This Year: {year_start} to {today}"
    else:
        period_desc = "All Time"
    
    # Create PDF response
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="sales_report_{payment_status}_{period}_{datetime.now().strftime("%Y%m%d")}.pdf"'
    
    # Create PDF document
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    
    # Container for the 'Flowable' objects
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        alignment=1,  # Center alignment
        textColor=colors.darkblue
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=12,
        textColor=colors.darkblue
    )
    
    # Title
    title = Paragraph(f"{owner.restaurant_name}<br/>SALES REPORT", title_style)
    elements.append(title)
    elements.append(Spacer(1, 20))
    
    # Report Information
    report_info = [
        ['Generated on:', datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
        ['Period:', period_desc],
        ['Payment Status Filter:', payment_status.title()],
    ]
    
    if category_id != 'all':
        try:
            category_name = MainCategory.objects.get(id=category_id, owner=owner).name
            report_info.append(['Category Filter:', category_name])
        except:
            report_info.append(['Category Filter:', f'Category ID {category_id}'])
    
    if subcategory_id != 'all':
        try:
            subcategory_name = SubCategory.objects.get(id=subcategory_id, main_category__owner=owner).name
            report_info.append(['Sub Category Filter:', subcategory_name])
        except:
            report_info.append(['Sub Category Filter:', f'Sub Category ID {subcategory_id}'])
    
    info_table = Table(report_info, colWidths=[2*inch, 4*inch])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    elements.append(info_table)
    elements.append(Spacer(1, 20))
    
    # Summary Statistics
    summary_heading = Paragraph("SUMMARY STATISTICS", heading_style)
    elements.append(summary_heading)
    
    summary_data = [
        ['Total Revenue:', f'${total_revenue:,.2f}'],
        ['Total Orders:', f'{total_orders:,}'],
        ['Items Sold:', f'{total_items:,}'],
        ['Average Order Value:', f'${avg_order_value:,.2f}']
    ]
    
    summary_table = Table(summary_data, colWidths=[2*inch, 2*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightblue),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    elements.append(summary_table)
    elements.append(Spacer(1, 30))
    
    # Detailed Sales Data
    detailed_heading = Paragraph("DETAILED SALES DATA", heading_style)
    elements.append(detailed_heading)
    
    # Table headers
    headers = ['Order #', 'Date', 'Customer', 'Items', 'Total', 'Payment', 'Status']
    data = [headers]
    
    # Table data
    for order in orders.order_by('-created_at'):
        items_list = ', '.join([f"{item.product.name} x{item.quantity}" for item in order.order_items.all()][:3])  # Limit items for PDF
        if len(order.order_items.all()) > 3:
            items_list += "..."
        
        customer_name = f"{order.ordered_by.first_name} {order.ordered_by.last_name}" if order.ordered_by else 'Walk-in'
        
        data.append([
            f"ORD-{order.id:08d}",
            order.created_at.strftime('%m/%d/%Y'),
            customer_name[:15],  # Limit length
            items_list[:25],  # Limit length
            f"${order.total_amount:.2f}",
            order.payment_status.title(),
            order.status.title()
        ])
    
    # Create table
    table = Table(data, colWidths=[1*inch, 0.8*inch, 1*inch, 2*inch, 0.8*inch, 0.8*inch, 0.8*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    elements.append(table)
    
    # Build PDF
    doc.build(elements)
    
    # Get the value of the BytesIO buffer and write it to the response
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)
    
    return response