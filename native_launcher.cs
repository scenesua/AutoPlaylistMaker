using System;
using System.ComponentModel;
using System.Diagnostics;
using System.Drawing;
using System.Drawing.Imaging;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices;
using System.Windows.Forms;

internal sealed class StartupSplash : Form
{
    [StructLayout(LayoutKind.Sequential, Pack = 1)]
    private struct BlendFunction
    {
        public byte BlendOp;
        public byte BlendFlags;
        public byte SourceConstantAlpha;
        public byte AlphaFormat;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct BitmapInfoHeader
    {
        public uint Size;
        public int Width;
        public int Height;
        public ushort Planes;
        public ushort BitCount;
        public uint Compression;
        public uint SizeImage;
        public int XPelsPerMeter;
        public int YPelsPerMeter;
        public uint ColorsUsed;
        public uint ColorsImportant;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct BitmapInfo
    {
        public BitmapInfoHeader Header;
        public uint Colors;
    }

    [DllImport("user32.dll", SetLastError = true)]
    private static extern IntPtr GetDC(IntPtr window);

    [DllImport("user32.dll", SetLastError = true)]
    private static extern int ReleaseDC(IntPtr window, IntPtr dc);

    [DllImport("gdi32.dll", SetLastError = true)]
    private static extern IntPtr CreateCompatibleDC(IntPtr dc);

    [DllImport("gdi32.dll", SetLastError = true)]
    private static extern IntPtr SelectObject(IntPtr dc, IntPtr drawingObject);

    [DllImport("gdi32.dll", SetLastError = true)]
    private static extern bool DeleteObject(IntPtr drawingObject);

    [DllImport("gdi32.dll", SetLastError = true)]
    private static extern bool DeleteDC(IntPtr dc);

    [DllImport("gdi32.dll", SetLastError = true)]
    private static extern IntPtr CreateDIBSection(
        IntPtr dc,
        ref BitmapInfo bitmapInfo,
        uint usage,
        out IntPtr bits,
        IntPtr section,
        uint offset
    );

    [DllImport("kernel32.dll", EntryPoint = "RtlMoveMemory")]
    private static extern void CopyMemory(
        IntPtr destination, IntPtr source, UIntPtr length
    );

    [DllImport("user32.dll", SetLastError = true)]
    private static extern bool UpdateLayeredWindow(
        IntPtr window,
        IntPtr destinationDc,
        ref Point destination,
        ref Size size,
        IntPtr sourceDc,
        ref Point source,
        int colorKey,
        ref BlendFunction blend,
        int flags
    );

    private readonly Bitmap image;

    internal StartupSplash(string imagePath)
    {
        image = new Bitmap(imagePath);
        ClientSize = image.Size;
        FormBorderStyle = FormBorderStyle.None;
        StartPosition = FormStartPosition.Manual;
        var area = Screen.PrimaryScreen.WorkingArea;
        Location = new Point(
            area.Left + (area.Width - image.Width) / 2,
            area.Top + (area.Height - image.Height) / 2
        );
        ShowInTaskbar = false;
        TopMost = true;
        AutoScaleMode = AutoScaleMode.None;
    }

    protected override CreateParams CreateParams
    {
        get
        {
            const int layered = 0x00080000;
            const int toolWindow = 0x00000080;
            var parameters = base.CreateParams;
            parameters.ExStyle |= layered | toolWindow;
            return parameters;
        }
    }

    protected override void OnShown(EventArgs eventArgs)
    {
        base.OnShown(eventArgs);
        RenderLayeredImage();
    }

    protected override void Dispose(bool disposing)
    {
        if (disposing)
        {
            image.Dispose();
        }
        base.Dispose(disposing);
    }

    private void RenderLayeredImage()
    {
        const int alphaBlend = 0x00000002;
        const byte sourceAlpha = 0x01;
        var screenDc = GetDC(IntPtr.Zero);
        var memoryDc = CreateCompatibleDC(screenDc);
        var bitmapInfo = new BitmapInfo
        {
            Header = new BitmapInfoHeader
            {
                Size = (uint)Marshal.SizeOf(typeof(BitmapInfoHeader)),
                Width = image.Width,
                Height = -image.Height,
                Planes = 1,
                BitCount = 32,
                Compression = 0,
                SizeImage = (uint)(image.Width * image.Height * 4),
            },
        };
        IntPtr bits;
        var bitmapHandle = CreateDIBSection(
            screenDc, ref bitmapInfo, 0, out bits, IntPtr.Zero, 0
        );
        var previous = SelectObject(memoryDc, bitmapHandle);
        BitmapData imageData = null;
        try
        {
            imageData = image.LockBits(
                new Rectangle(0, 0, image.Width, image.Height),
                ImageLockMode.ReadOnly,
                PixelFormat.Format32bppPArgb
            );
            var rowBytes = image.Width * 4;
            for (var row = 0; row < image.Height; row++)
            {
                CopyMemory(
                    IntPtr.Add(bits, row * rowBytes),
                    IntPtr.Add(imageData.Scan0, row * imageData.Stride),
                    (UIntPtr)(uint)rowBytes
                );
            }
            var destination = Location;
            var source = Point.Empty;
            var size = image.Size;
            var blend = new BlendFunction
            {
                BlendOp = 0,
                BlendFlags = 0,
                SourceConstantAlpha = 255,
                AlphaFormat = sourceAlpha,
            };
            if (!UpdateLayeredWindow(
                Handle,
                screenDc,
                ref destination,
                ref size,
                memoryDc,
                ref source,
                0,
                ref blend,
                alphaBlend
            ))
            {
                throw new Win32Exception(Marshal.GetLastWin32Error());
            }
        }
        finally
        {
            if (imageData != null)
            {
                image.UnlockBits(imageData);
            }
            SelectObject(memoryDc, previous);
            DeleteObject(bitmapHandle);
            DeleteDC(memoryDc);
            ReleaseDC(IntPtr.Zero, screenDc);
        }
    }
}

internal static class Program
{
    [DllImport("user32.dll")]
    private static extern bool IsWindowVisible(IntPtr window);

    private static string Quote(string value)
    {
        if (value.Length > 0 && !value.Any(char.IsWhiteSpace)
            && value.IndexOf('"') < 0)
        {
            return value;
        }
        return "\"" + value.Replace("\\", "\\\\").Replace("\"", "\\\"") + "\"";
    }

    private static IntPtr FindVisibleCoreWindow(
        string corePath, DateTime earliestStart, out bool hasRunningCore
    )
    {
        hasRunningCore = false;
        var processName = Path.GetFileNameWithoutExtension(corePath);
        foreach (var process in Process.GetProcessesByName(processName))
        {
            using (process)
            {
                try
                {
                    if (process.HasExited
                        || process.StartTime < earliestStart
                        || !string.Equals(
                            process.MainModule.FileName,
                            corePath,
                            StringComparison.OrdinalIgnoreCase
                        ))
                    {
                        continue;
                    }
                    hasRunningCore = true;
                    process.Refresh();
                    var window = process.MainWindowHandle;
                    if (window != IntPtr.Zero && IsWindowVisible(window))
                    {
                        return window;
                    }
                }
                catch
                {
                    // A process may exit between enumeration and inspection.
                }
            }
        }
        return IntPtr.Zero;
    }

    [STAThread]
    private static void Main(string[] args)
    {
        var baseDir = AppDomain.CurrentDomain.BaseDirectory;
        var corePath = Path.Combine(
            baseDir, "AutoPlaylistMaker_v1.3.0.core.exe"
        );
        var splashPath = Path.Combine(baseDir, "app_splash.png");
        if (!File.Exists(corePath) || !File.Exists(splashPath))
        {
            MessageBox.Show(
                "The application package is incomplete.",
                "Auto Playlist Maker",
                MessageBoxButtons.OK,
                MessageBoxIcon.Error
            );
            return;
        }

        Application.EnableVisualStyles();
        Application.SetCompatibleTextRenderingDefault(false);
        using (var splash = new StartupSplash(splashPath))
        {
            Process core = null;
            var coreStartedAt = DateTime.MaxValue;
            var monitor = new Timer { Interval = 100 };
            splash.Shown += (_, __) =>
            {
                var forwarded = args.Concat(
                    new[] { "--launcher-splash" }
                ).Select(Quote);
                coreStartedAt = DateTime.Now.AddSeconds(-1);
                core = Process.Start(new ProcessStartInfo
                {
                    FileName = corePath,
                    Arguments = string.Join(" ", forwarded),
                    WorkingDirectory = baseDir,
                    UseShellExecute = false,
                });
                monitor.Start();
            };
            monitor.Tick += (_, __) =>
            {
                if (core == null)
                {
                    return;
                }
                bool hasRunningCore;
                var visibleWindow = FindVisibleCoreWindow(
                    corePath, coreStartedAt, out hasRunningCore
                );
                if (visibleWindow != IntPtr.Zero)
                {
                    monitor.Stop();
                    splash.Close();
                    return;
                }
                if (core.HasExited && !hasRunningCore)
                {
                    monitor.Stop();
                    splash.Close();
                    if (core.ExitCode != 0)
                    {
                        MessageBox.Show(
                            "The application could not be started.",
                            "Auto Playlist Maker",
                            MessageBoxButtons.OK,
                            MessageBoxIcon.Error
                        );
                    }
                    return;
                }
            };
            Application.Run(splash);
            monitor.Dispose();
        }
    }
}
