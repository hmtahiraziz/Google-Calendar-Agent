import { useCallback, useState } from 'react'
import Toast from '../components/Toast'

export default function useToast() {
  const [visible, setVisible] = useState(false)
  const [message, setMessage] = useState('')

  const show = useCallback((m) => {
    setMessage(m)
    setVisible(true)
  }, [])

  const hide = useCallback(() => setVisible(false), [])

  const ToastElement = useCallback(() => (
    <Toast message={message} visible={visible} onHide={hide} />
  ), [message, visible, hide])

  return { show, hide, Toast: ToastElement }
}

