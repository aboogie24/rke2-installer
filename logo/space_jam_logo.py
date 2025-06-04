import random
import time
import colorama
import click

def display_space_jam_logo1():
    """Display a Space Jam themed logo with stars and cosmic effects"""
    logo = f"""
    {colorama.Fore.CYAN}★ * ✧ ✦ * ✧ ★ ✦ * ✧ {colorama.Fore.WHITE}★{colorama.Fore.CYAN} ✦ * ✧ ★ ✦ * ✧ {colorama.Fore.WHITE}★{colorama.Fore.CYAN} ✦ * ✧ ★ ✦ * ✧ ★ * ✧

    {colorama.Fore.YELLOW} ███████ ██████   █████   ██████ ███████{colorama.Fore.MAGENTA}      ██████  █████  ███    ███ 
    {colorama.Fore.YELLOW}██      ██    ██ ██   ██ ██      ██     {colorama.Fore.MAGENTA}         ██ ██   ██ ████  ████ 
    {colorama.Fore.YELLOW}███████ ██████  ███████ ██      █████   {colorama.Fore.MAGENTA}         ██ ███████ ██ ████ ██ 
    {colorama.Fore.YELLOW}     ██ ██      ██   ██ ██      ██      {colorama.Fore.MAGENTA}  ██    ██ ██   ██ ██  ██  ██ 
    {colorama.Fore.YELLOW}███████ ██      ██   ██  ██████ ███████ {colorama.Fore.MAGENTA}   ██████  ██   ██ ██      ██ 

    {colorama.Fore.WHITE}{colorama.Style.BRIGHT}       ★ {colorama.Fore.CYAN}RKE2 {colorama.Fore.WHITE}Airgapped Kubernetes {colorama.Fore.YELLOW}Deployment {colorama.Fore.CYAN}Tool{colorama.Fore.WHITE} ★       

    {colorama.Fore.CYAN}★ * ✧ ✦ * ✧ ★ ✦ * ✧ {colorama.Fore.WHITE}★{colorama.Fore.CYAN} ✦ * ✧ ★ ✦ * ✧ {colorama.Fore.WHITE}★{colorama.Fore.CYAN} ✦ * ✧ ★ ✦ * ✧ ★ * ✧
    """
    
    click.echo(logo)

def display_space_jam_logo4():
    """Display a Space Jam themed logo with stars and cosmic effects"""
    logo = f"""
    {colorama.Fore.CYAN}★ * ✧ ✦ * ✧ ★ ✦ * ✧ {colorama.Fore.WHITE}★{colorama.Fore.CYAN} ✦ * ✧ ★ ✦ * ✧ {colorama.Fore.WHITE}★{colorama.Fore.CYAN} ✦ * ✧ ★ ✦ * ✧ ★ * ✧

    {colorama.Fore.YELLOW} ███████ ██████   █████   ██████ ███████{colorama.Fore.MAGENTA}      ██████  █████  ███    ███ 
    {colorama.Fore.YELLOW}██      ██    ██ ██   ██ ██      ██     {colorama.Fore.MAGENTA}         ██ ██   ██ ████  ████ 
    {colorama.Fore.YELLOW}███████ ██████  ███████ ██      █████   {colorama.Fore.MAGENTA}         ██ ███████ ██ ████ ██ 
    {colorama.Fore.YELLOW}     ██ ██      ██   ██ ██      ██      {colorama.Fore.MAGENTA}  ██    ██ ██   ██ ██  ██  ██ 
    {colorama.Fore.YELLOW}███████ ██      ██   ██  ██████ ███████ {colorama.Fore.MAGENTA}   ██████  ██   ██ ██      ██ 

    {colorama.Fore.WHITE}{colorama.Style.BRIGHT}       ★ {colorama.Fore.CYAN}RKE2 {colorama.Fore.WHITE}Airgapped Kubernetes {colorama.Fore.YELLOW}Deployment {colorama.Fore.CYAN}Tool{colorama.Fore.WHITE} ★       
    {colorama.Fore.CYAN}{colorama.Style.BRIGHT}                Created by: {colorama.Fore.GREEN}The Astronaut(AB)                 

    {colorama.Fore.CYAN}★ * ✧ ✦ * ✧ ★ ✦ * ✧ {colorama.Fore.WHITE}★{colorama.Fore.CYAN} ✦ * ✧ ★ ✦ * ✧ {colorama.Fore.WHITE}★{colorama.Fore.CYAN} ✦ * ✧ ★ ✦ * ✧ ★ * ✧
    """
    
    click.echo(logo)

def display_space_jam_logo2():
    """Display a Space Jam themed logo with stars"""
    space_part = """
     ██████  ██████   █████   ██████ ███████    
    ██      ██    ██ ██   ██ ██      ██         
     █████  ██████  ███████ ██      █████       
         ██ ██      ██   ██ ██      ██          
    ██████  ██      ██   ██  ██████ ███████     
    """
    
    jam_part = """
     ██  █████  ███    ███ 
    ███ ██   ██ ████  ████ 
     ██ ███████ ██ ████ ██ 
     ██ ██   ██ ██  ██  ██ 
     ██ ██   ██ ██      ██ 
    """
    
    stars_top = " ⭐ ⭐ ⭐ ⭐ ⭐ ⭐ ⭐ ⭐ ⭐ ⭐ ⭐ ⭐ ⭐ ⭐ ⭐ ⭐ ⭐ ⭐ ⭐ ⭐ ⭐ ⭐ ⭐ ⭐"
    subtitle = "           ★ RKE2 Airgapped Deployment Tool ★           "
    stars_bottom = " ⭐ ⭐ ⭐ ⭐ ⭐ ⭐ ⭐ ⭐ ⭐ ⭐ ⭐ ⭐ ⭐ ⭐ ⭐ ⭐ ⭐ ⭐ ⭐ ⭐ ⭐ ⭐ ⭐ ⭐"
    
    # Display logo components with colors
    click.echo("\n" + colorama.Fore.CYAN + stars_top)
    click.echo("")
    
    # Display SPACE in yellow
    for line in space_part.strip().split('\n'):
        click.echo(colorama.Fore.YELLOW + line + colorama.Fore.MAGENTA + jam_part.strip().split('\n')[space_part.strip().split('\n').index(line)])
    
    click.echo("")
    click.echo(colorama.Fore.WHITE + colorama.Style.BRIGHT + subtitle)
    click.echo("")
    click.echo(colorama.Fore.CYAN + stars_bottom + "\n")

def display_space_jam_logo3():
    """Display a Space Jam themed logo with stars and cosmic effects"""
    logo = f"""
    {colorama.Fore.CYAN}★ * ✧ ✦ * ✧ ★ ✦ * ✧ {colorama.Fore.WHITE}★{colorama.Fore.CYAN} ✦ * ✧ ★ ✦ * ✧ {colorama.Fore.WHITE}★{colorama.Fore.CYAN} ✦ * ✧ ★ ✦ * ✧ ★ * ✧

    {colorama.Fore.YELLOW} ███████ ██████   █████   ██████ ███████{colorama.Fore.MAGENTA}      ██  █████  ███    ███ 
    {colorama.Fore.YELLOW}██      ██    ██ ██   ██ ██      ██     {colorama.Fore.MAGENTA}    ███ ██   ██ ████  ████ 
    {colorama.Fore.YELLOW}███████ ██████  ███████ ██      █████   {colorama.Fore.MAGENTA}     ██ ███████ ██ ████ ██ 
    {colorama.Fore.YELLOW}     ██ ██      ██   ██ ██      ██      {colorama.Fore.MAGENTA}     ██ ██   ██ ██  ██  ██ 
    {colorama.Fore.YELLOW}███████ ██      ██   ██  ██████ ███████ {colorama.Fore.MAGENTA}     ██ ██   ██ ██      ██ 

    {colorama.Fore.WHITE}{colorama.Style.BRIGHT}       ★ {colorama.Fore.CYAN}RKE2 {colorama.Fore.WHITE}Airgapped Kubernetes {colorama.Fore.YELLOW}Deployment {colorama.Fore.CYAN}Tool{colorama.Fore.WHITE} ★       

    {colorama.Fore.CYAN}★ * ✧ ✦ * ✧ ★ ✦ * ✧ {colorama.Fore.WHITE}★{colorama.Fore.CYAN} ✦ * ✧ ★ ✦ * ✧ {colorama.Fore.WHITE}★{colorama.Fore.CYAN} ✦ * ✧ ★ ✦ * ✧ ★ * ✧
    """
    
    click.echo(logo)

def display_animated_logo():
    """Display an animated Space Jam logo with stars"""
    # Clear screen first
    click.clear()
    
    # Define star characters for animation
    stars = ['✦', '✧', '★', '*', '⭐']
    
    # Perform a small starfield animation
    for _ in range(5):
        # Display random stars
        for i in range(10):
            x = random.randint(0, 70)
            y = random.randint(0, 15)
            star = random.choice(stars)
            color = random.choice([colorama.Fore.CYAN, colorama.Fore.WHITE, colorama.Fore.YELLOW])
            # Position cursor and print star
            click.echo(f"\033[{y};{x}H{color}{star}")
        time.sleep(0.2)
    
    # Clear screen again
    click.clear()
    
    # Now display the actual logo
    display_space_jam_logo4()